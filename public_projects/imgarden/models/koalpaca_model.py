"""
KoAlpaca 모델 래퍼 클래스
RTX 3060 Ti 최적화, 메모리 관리 포함
"""

import torch
from transformers import (
    AutoTokenizer, AutoModelForCausalLM,
    GenerationConfig, StoppingCriteria, StoppingCriteriaList
)
from peft import get_peft_model, PeftModel
import logging
from typing import List, Dict, Optional, Tuple, Union
import time
import gc
import re
from pathlib import Path

from .models_config import ModelConfigManager

logger = logging.getLogger(__name__)

class CustomStoppingCriteria(StoppingCriteria):
    """커스텀 정지 조건"""

    def __init__(self, stop_words: List[str], tokenizer):
        self.stop_words = stop_words
        self.tokenizer = tokenizer
        self.stop_token_ids = []

        # 정지 단어들을 토큰 ID로 변환
        for word in stop_words:
            token_ids = tokenizer.encode(word, add_special_tokens=False)
            self.stop_token_ids.extend(token_ids)

    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor, **kwargs) -> bool:
        # 마지막 생성된 토큰이 정지 토큰인지 확인
        last_token = input_ids[0][-1].item()
        return last_token in self.stop_token_ids

class KoAlpacaModel:
    """KoAlpaca 모델 래퍼"""

    def __init__(self, model_config, config_manager: Optional[ModelConfigManager] = None):
        """
        Args:
            model_config: ModelConfig 객체
            config_manager: ModelConfigManager (선택사항)
        """
        self.config = model_config
        self.config_manager = config_manager or ModelConfigManager(model_config)

        # 모델 관련 변수
        self.tokenizer = None
        self.model = None
        self.peft_model = None
        self.generation_config = None

        # 성능 추적
        self.generation_stats = {
            "total_generations": 0,
            "total_time": 0.0,
            "avg_tokens_per_sec": 0.0
        }

        # 나비얌 특화 정지 단어
        self.naviyam_stop_words = [
            "사용자:", "User:", "AI:", "Assistant:",
            "###", "---", "[END]"
        ]

    def load_model(self, cache_dir: Optional[str] = None):
        """모델과 토크나이저 로드"""
        try:
            logger.info(f"모델 로딩 시작: {self.config.model_name}")
            start_time = time.time()

            # 토크나이저 로드
            self._load_tokenizer(cache_dir)

            # 모델 로드
            self._load_base_model(cache_dir)

            # Generation Config 설정
            self._setup_generation_config()

            # 메모리 체크
            memory_ok, memory_msg = self.config_manager.check_memory_limits()
            if not memory_ok:
                logger.error(f"메모리 부족: {memory_msg}")
                raise RuntimeError(f"메모리 부족: {memory_msg}")

            load_time = time.time() - start_time
            logger.info(f"모델 로딩 완료: {load_time:.2f}초")

            # 설정 요약 출력
            self.config_manager.print_config_summary()

        except Exception as e:
            logger.error(f"모델 로딩 실패: {e}")
            raise

    def _load_tokenizer(self, cache_dir: Optional[str] = None):
        """토크나이저 로드"""
        logger.info("토크나이저 로딩...")

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.config.model_name,
            cache_dir=cache_dir,
            trust_remote_code=True
        )

        # 패딩 토큰 설정
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
            logger.info("패딩 토큰을 EOS 토큰으로 설정")

        logger.info(f"토크나이저 로드 완료: {len(self.tokenizer)} 토큰")

    def _load_base_model(self, cache_dir: Optional[str] = None):
        """기본 모델 로드"""
        logger.info("기본 모델 로딩...")

        # 모델 로드 kwargs 가져오기
        model_kwargs = self.config_manager.get_model_kwargs()
        if cache_dir:
            model_kwargs["cache_dir"] = cache_dir

        self.model = AutoModelForCausalLM.from_pretrained(
            self.config.model_name,
            **model_kwargs
        )

        # 모델을 evaluation 모드로 설정
        self.model.eval()

        logger.info("기본 모델 로드 완료")

    def _setup_generation_config(self):
        """텍스트 생성 설정"""
        generation_kwargs = self.config_manager.get_generation_kwargs()

        # 토크나이저 토큰 설정
        generation_kwargs["pad_token_id"] = self.tokenizer.pad_token_id
        generation_kwargs["eos_token_id"] = self.tokenizer.eos_token_id

        self.generation_config = GenerationConfig(**generation_kwargs)
        logger.info("Generation Config 설정 완료")

    def setup_lora(self, lora_path: Optional[str] = None):
        """LoRA 어댑터 설정"""
        try:
            if lora_path and Path(lora_path).exists():
                # 기존 LoRA 어댑터 로드
                logger.info(f"LoRA 어댑터 로드: {lora_path}")
                self.peft_model = PeftModel.from_pretrained(
                    self.model,
                    lora_path,
                    is_trainable=False
                )
            else:
                # 새 LoRA 어댑터 생성
                logger.info("새 LoRA 어댑터 생성")
                lora_config = self.config_manager.get_lora_config()
                self.peft_model = get_peft_model(self.model, lora_config)

            logger.info("LoRA 설정 완료")

        except Exception as e:
            logger.error(f"LoRA 설정 실패: {e}")
            # LoRA 없이도 동작하도록 fallback
            self.peft_model = None

    def generate_text(
        self,
        prompt: str,
        max_new_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop_words: Optional[List[str]] = None
    ) -> Dict[str, Union[str, float, int]]:
        """텍스트 생성"""
        if self.model is None:
            raise RuntimeError("모델이 로드되지 않음. load_model()을 먼저 호출하세요")

        start_time = time.time()

        try:
            # 입력 토큰화
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=self.config.max_length - (max_new_tokens or 200),
                return_token_type_ids=False
            )

            # print(f"DEBUG: inputs type = {type(inputs)}")
            # print(f"DEBUG: inputs keys = {list(inputs.keys()) if hasattr(inputs, 'keys') else 'NO KEYS'}")
            # print(f"DEBUG: inputs = {inputs}")

            if 'token_type_ids' in inputs:
                del inputs['token_type_ids']

            if torch.cuda.is_available():
                inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

            # print(f"DEBUG: After GPU move - inputs type = {type(inputs)}")
            # print(
            #     f"DEBUG: After GPU move - inputs keys = {list(inputs.keys()) if hasattr(inputs, 'keys') else 'NO KEYS'}")

            # 생성 설정 조정
            generation_config = self.generation_config
            if max_new_tokens:
                generation_config.max_new_tokens = max_new_tokens
            if temperature:
                generation_config.temperature = temperature

            # 정지 조건 설정
            stopping_criteria = None
            if stop_words:
                combined_stop_words = self.naviyam_stop_words + stop_words
                stopping_criteria = StoppingCriteriaList([
                    CustomStoppingCriteria(combined_stop_words, self.tokenizer)
                ])

            # 모델 선택 (LoRA 있으면 LoRA 사용)
            model_to_use = self.peft_model if self.peft_model else self.model

            # 텍스트 생성
            with torch.no_grad():
                # inputs에서 필요한 것만 추출
                generate_kwargs = {
                    'input_ids': inputs['input_ids'],
                    'generation_config': generation_config,
                    'return_dict_in_generate': True,
                    'output_scores': True
                }

                # attention_mask가 있으면 추가
                if 'attention_mask' in inputs:
                    generate_kwargs['attention_mask'] = inputs['attention_mask']

                # stopping_criteria가 있으면 추가
                if stopping_criteria:
                    generate_kwargs['stopping_criteria'] = stopping_criteria

                outputs = model_to_use.generate(**generate_kwargs)

            # 결과 디코딩
            generated_tokens = outputs.sequences[0][inputs['input_ids'].shape[1]:]
            generated_text = self.tokenizer.decode(generated_tokens, skip_special_tokens=True)

            # 통계 업데이트
            generation_time = time.time() - start_time
            num_tokens = len(generated_tokens)

            self._update_stats(generation_time, num_tokens)

            # 후처리
            cleaned_text = self._postprocess_text(generated_text)

            result = {
                "text": cleaned_text,
                "raw_text": generated_text,
                "tokens_generated": num_tokens,
                "generation_time": generation_time,
                "tokens_per_second": num_tokens / generation_time if generation_time > 0 else 0,
                "prompt_tokens": inputs['input_ids'].shape[1]
            }

            logger.debug(f"생성 완료: {num_tokens}토큰, {generation_time:.2f}초")

            return result

        except Exception as e:
            logger.error(f"텍스트 생성 실패: {e}")
            return {
                "text": "",
                "error": str(e),
                "generation_time": time.time() - start_time
            }

    def _postprocess_text(self, text: str) -> str:
        """생성된 텍스트 후처리"""
        # 불필요한 공백 제거
        cleaned = text.strip()

        # 정지 단어 제거
        for stop_word in self.naviyam_stop_words:
            if stop_word in cleaned:
                cleaned = cleaned.split(stop_word)[0].strip()

        cleaned = re.sub(r'[#\[\]]\.?', '', cleaned)  # #. <br. [] 제거
        cleaned = re.sub(r'\{이름\}|\{음식.*?\}', '', cleaned)  # 빈 한글 플레이스홀더만 제거
        cleaned = re.sub(r'\[이름\]|\[음식.*?\]', '', cleaned)  # 대괄호 한글 플레이스홀더 제거
        cleaned = re.sub(r'Ø', '', cleaned)  # 특수문자 제거
        cleaned = re.sub(r'친근한 목소리로.*', '', cleaned)  # 이상한 지시문 제거
        cleaned = re.sub(r'친근한 음식:.*', '', cleaned)  # 이상한 지시문 제거
        cleaned = re.sub(r'<.*?>', '', cleaned)  # HTML 태그 제거
        cleaned = re.sub(r'\s+', ' ', cleaned)  # 중복 공백 제거

        # 중복된 문장 제거 (간단한 버전)
        sentences = cleaned.split('.')
        unique_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and sentence not in unique_sentences:
                unique_sentences.append(sentence)

        if unique_sentences:
            cleaned = '. '.join(unique_sentences)
            if not cleaned.endswith('.'):
                cleaned += '.'

        return cleaned

    def _update_stats(self, generation_time: float, num_tokens: int):
        """성능 통계 업데이트"""
        self.generation_stats["total_generations"] += 1
        self.generation_stats["total_time"] += generation_time

        if self.generation_stats["total_time"] > 0:
            total_tokens = self.generation_stats["total_generations"] * num_tokens
            self.generation_stats["avg_tokens_per_sec"] = (
                total_tokens / self.generation_stats["total_time"]
            )

    def get_embeddings(self, text: str) -> torch.Tensor:
        """텍스트 임베딩 추출"""
        if self.model is None:
            raise RuntimeError("모델이 로드되지 않음")

        inputs = self.tokenizer(text, return_tensors="pt", truncation=True)
        if torch.cuda.is_available():
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs, output_hidden_states=True)
            # 마지막 레이어의 평균 풀링
            embeddings = outputs.hidden_states[-1].mean(dim=1)

        return embeddings

    def save_lora_adapter(self, save_path: str):
        """LoRA 어댑터 저장"""
        if self.peft_model is None:
            logger.warning("저장할 LoRA 어댑터 없음")
            return

        save_dir = Path(save_path)
        save_dir.mkdir(parents=True, exist_ok=True)

        self.peft_model.save_pretrained(save_dir)
        logger.info(f"LoRA 어댑터 저장: {save_dir}")

    def cleanup_memory(self):
        """메모리 정리"""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        gc.collect()
        logger.info("메모리 정리 완료")

    def get_model_info(self) -> Dict:
        """모델 정보 반환"""
        info = {
            "model_name": self.config.model_name,
            "device": str(self.model.device) if self.model else "None",
            "quantization": "4bit" if self.config.use_4bit else "8bit" if self.config.use_8bit else "None",
            "lora_enabled": self.peft_model is not None,
            "generation_stats": self.generation_stats.copy()
        }

        if self.model:
            info["total_params"] = sum(p.numel() for p in self.model.parameters())
            info["trainable_params"] = sum(p.numel() for p in self.model.parameters() if p.requires_grad)

        return info

    def benchmark_generation(self, test_prompts: List[str], num_runs: int = 3) -> Dict:
        """생성 성능 벤치마크"""
        if not test_prompts:
            test_prompts = [
                "안녕하세요! 맛있는 음식 추천해주세요.",
                "만원으로 먹을 수 있는 메뉴가 있나요?",
                "친구랑 같이 갈 만한 가게 알려주세요."
            ]

        results = []

        for prompt in test_prompts:
            prompt_results = []

            for _ in range(num_runs):
                result = self.generate_text(prompt, max_new_tokens=100)
                if "error" not in result:
                    prompt_results.append({
                        "tokens_per_second": result["tokens_per_second"],
                        "generation_time": result["generation_time"],
                        "tokens_generated": result["tokens_generated"]
                    })

            if prompt_results:
                avg_tps = sum(r["tokens_per_second"] for r in prompt_results) / len(prompt_results)
                avg_time = sum(r["generation_time"] for r in prompt_results) / len(prompt_results)

                results.append({
                    "prompt": prompt[:50] + "...",
                    "avg_tokens_per_second": avg_tps,
                    "avg_generation_time": avg_time,
                    "runs": len(prompt_results)
                })

        return {
            "benchmark_results": results,
            "overall_avg_tps": sum(r["avg_tokens_per_second"] for r in results) / len(results) if results else 0
        }

    def __del__(self):
        """소멸자에서 메모리 정리"""
        try:
            self.cleanup_memory()
        except:
            pass

# 편의 함수들
def create_koalpaca_model(model_config, cache_dir: Optional[str] = None) -> KoAlpacaModel:
    """KoAlpaca 모델 생성 및 로드"""
    model = KoAlpacaModel(model_config)
    model.load_model(cache_dir)
    return model

def quick_generate(model_config, prompt: str, cache_dir: Optional[str] = None) -> str:
    """빠른 텍스트 생성 (테스트용)"""
    model = create_koalpaca_model(model_config, cache_dir)
    result = model.generate_text(prompt)
    model.cleanup_memory()
    return result.get("text", "")