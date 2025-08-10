"""
LoRA 어댑터 배포 관리
어댑터 배포, 버전 관리, 백업, 롤백, 정리를 담당하는 클래스
"""

import logging
import shutil
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class LoRADeploymentManager:
    """LoRA 어댑터 배포 관리 클래스"""
    
    def __init__(self, 
                 adapter_dir: str = "./outputs/lora_adapters",
                 production_dir: str = "./outputs/production_adapters",
                 backup_dir: str = "./outputs/adapter_backups"):
        """
        Args:
            adapter_dir: 학습된 어댑터 저장 디렉토리
            production_dir: 프로덕션 어댑터 디렉토리  
            backup_dir: 백업 어댑터 디렉토리
        """
        self.adapter_dir = Path(adapter_dir)
        self.production_dir = Path(production_dir)
        self.backup_dir = Path(backup_dir)
        
        # 디렉토리 생성
        self.adapter_dir.mkdir(parents=True, exist_ok=True)
        self.production_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 배포 기록 파일
        self.deployment_log_file = self.production_dir / "deployment_log.json"
        self.deployment_log = self._load_deployment_log()
        
        logger.info("LoRADeploymentManager 초기화 완료")
    
    def deploy_adapter(self, adapter_name: str, performance: Dict[str, float],
                      force_deploy: bool = False) -> Dict[str, Any]:
        """어댑터 배포
        
        Args:
            adapter_name: 배포할 어댑터 이름
            performance: 어댑터 성능 지표
            force_deploy: 강제 배포 여부
            
        Returns:
            배포 결과 정보
        """
        logger.info(f"어댑터 배포 시작: {adapter_name}")
        
        try:
            # 1. 어댑터 파일 존재 확인
            adapter_path = self.adapter_dir / adapter_name
            if not adapter_path.exists():
                raise FileNotFoundError(f"어댑터를 찾을 수 없습니다: {adapter_path}")
            
            # 2. 배포 적합성 확인 (강제 배포가 아닌 경우)
            if not force_deploy:
                deployment_check = self._check_deployment_eligibility(adapter_name, performance)
                if not deployment_check["eligible"]:
                    return {
                        "success": False,
                        "reason": deployment_check["reason"],
                        "adapter_name": adapter_name
                    }
            
            # 3. 현재 프로덕션 어댑터 백업
            current_production = self._get_current_production_adapter()
            if current_production:
                self._backup_current_adapter(current_production)
            
            # 4. 새 어댑터를 프로덕션으로 복사
            production_path = self.production_dir / "current"
            if production_path.exists():
                shutil.rmtree(production_path)
            
            shutil.copytree(adapter_path, production_path)
            
            # 5. 배포 기록 업데이트
            deployment_record = {
                "adapter_name": adapter_name,
                "deployed_at": datetime.now().isoformat(),
                "performance": performance,
                "previous_adapter": current_production,
                "deployment_method": "force" if force_deploy else "auto"
            }
            
            self.deployment_log.append(deployment_record)
            self._save_deployment_log()
            
            # 6. 메타데이터 파일 생성
            self._create_production_metadata(deployment_record)
            
            logger.info(f"어댑터 배포 완료: {adapter_name}")
            
            return {
                "success": True,
                "adapter_name": adapter_name,
                "deployed_at": deployment_record["deployed_at"],
                "performance": performance,
                "production_path": str(production_path)
            }
            
        except Exception as e:
            logger.error(f"어댑터 배포 실패: {adapter_name} - {e}")
            return {
                "success": False,
                "adapter_name": adapter_name,
                "error": str(e)
            }
    
    def rollback_adapter(self, target_adapter: str = None) -> Dict[str, Any]:
        """어댑터 롤백
        
        Args:
            target_adapter: 롤백할 대상 어댑터 (None이면 이전 버전으로)
            
        Returns:
            롤백 결과 정보
        """
        logger.info(f"어댑터 롤백 시작: {target_adapter or '이전 버전'}")
        
        try:
            # 1. 롤백 대상 결정
            if target_adapter is None:
                # 가장 최근 배포의 이전 어댑터로 롤백
                if len(self.deployment_log) < 2:
                    raise ValueError("롤백할 이전 버전이 없습니다")
                
                target_adapter = self.deployment_log[-2]["adapter_name"]
            
            # 2. 대상 어댑터 백업 파일 확인
            backup_path = self.backup_dir / target_adapter
            if not backup_path.exists():
                raise FileNotFoundError(f"롤백 대상 어댑터 백업을 찾을 수 없습니다: {backup_path}")
            
            # 3. 현재 프로덕션 어댑터 백업
            current_adapter = self._get_current_production_adapter()
            if current_adapter:
                self._backup_current_adapter(current_adapter)
            
            # 4. 롤백 실행
            production_path = self.production_dir / "current"
            if production_path.exists():
                shutil.rmtree(production_path)
            
            shutil.copytree(backup_path, production_path)
            
            # 5. 롤백 기록
            rollback_record = {
                "adapter_name": target_adapter,
                "deployed_at": datetime.now().isoformat(),
                "deployment_method": "rollback",
                "rolled_back_from": current_adapter
            }
            
            self.deployment_log.append(rollback_record)
            self._save_deployment_log()
            
            logger.info(f"어댑터 롤백 완료: {target_adapter}")
            
            return {
                "success": True,
                "target_adapter": target_adapter,
                "rolled_back_from": current_adapter,
                "deployed_at": rollback_record["deployed_at"]
            }
            
        except Exception as e:
            logger.error(f"어댑터 롤백 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def cleanup_old_adapters(self, keep_count: int = 5) -> Dict[str, Any]:
        """오래된 어댑터 정리
        
        Args:
            keep_count: 유지할 어댑터 수
            
        Returns:
            정리 결과 정보
        """
        logger.info(f"오래된 어댑터 정리 시작 (유지 개수: {keep_count})")
        
        try:
            # 1. 어댑터 디렉토리 목록 조회
            adapter_dirs = [d for d in self.adapter_dir.iterdir() if d.is_dir()]
            
            # 2. 생성 시간 기준으로 정렬 (최신 순)
            adapter_dirs.sort(key=lambda x: x.stat().st_ctime, reverse=True)
            
            # 3. 유지할 어댑터와 삭제할 어댑터 분리
            keep_adapters = adapter_dirs[:keep_count]
            delete_adapters = adapter_dirs[keep_count:]
            
            # 4. 프로덕션 어댑터는 보호
            current_production = self._get_current_production_adapter()
            if current_production:
                production_path = self.adapter_dir / current_production
                if production_path in delete_adapters:
                    delete_adapters.remove(production_path)
                    if production_path not in keep_adapters:
                        keep_adapters.append(production_path)
            
            # 5. 오래된 어댑터 삭제
            deleted_adapters = []
            for adapter_path in delete_adapters:
                try:
                    shutil.rmtree(adapter_path)
                    deleted_adapters.append(adapter_path.name)
                    logger.debug(f"어댑터 삭제: {adapter_path.name}")
                except Exception as e:
                    logger.warning(f"어댑터 삭제 실패: {adapter_path.name} - {e}")
            
            # 6. 오래된 백업도 정리 (30일 이상)
            old_backups = self._cleanup_old_backups(days=30)
            
            cleanup_result = {
                "success": True,
                "total_adapters": len(adapter_dirs),
                "kept_adapters": len(keep_adapters),
                "deleted_adapters": len(deleted_adapters),
                "deleted_adapter_names": deleted_adapters,
                "deleted_backups": old_backups,
                "current_production": current_production
            }
            
            logger.info(f"어댑터 정리 완료: {len(deleted_adapters)}개 삭제, {len(keep_adapters)}개 유지")
            
            return cleanup_result
            
        except Exception as e:
            logger.error(f"어댑터 정리 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_deployment_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """배포 기록 조회
        
        Args:
            limit: 조회할 기록 수
            
        Returns:
            배포 기록 리스트 (최신순)
        """
        return self.deployment_log[-limit:] if self.deployment_log else []
    
    def get_current_production_info(self) -> Dict[str, Any]:
        """현재 프로덕션 어댑터 정보 조회"""
        current_adapter = self._get_current_production_adapter()
        
        if not current_adapter or not self.deployment_log:
            return {"status": "no_production_adapter"}
        
        # 가장 최근 배포 기록 찾기
        latest_deployment = None
        for record in reversed(self.deployment_log):
            if record["adapter_name"] == current_adapter:
                latest_deployment = record
                break
        
        production_path = self.production_dir / "current"
        metadata_file = production_path / "production_metadata.json"
        
        info = {
            "adapter_name": current_adapter,
            "production_path": str(production_path),
            "has_metadata": metadata_file.exists()
        }
        
        if latest_deployment:
            info.update({
                "deployed_at": latest_deployment["deployed_at"],
                "performance": latest_deployment.get("performance", {}),
                "deployment_method": latest_deployment.get("deployment_method", "unknown")
            })
        
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                info["metadata"] = metadata
            except Exception as e:
                logger.warning(f"메타데이터 로드 실패: {e}")
        
        return info
    
    def _check_deployment_eligibility(self, adapter_name: str, 
                                    performance: Dict[str, float]) -> Dict[str, Any]:
        """배포 적합성 검사"""
        # 기본 성능 기준
        min_overall_score = 0.7
        max_response_time = 5.0
        min_test_pass_rate = 0.5
        
        overall_score = performance.get("overall_score", 0.0)
        response_time = performance.get("avg_response_time", 999.0)
        test_cases_passed = performance.get("test_cases_passed", 0)
        total_test_cases = performance.get("total_test_cases", 1)
        pass_rate = test_cases_passed / total_test_cases
        
        if overall_score < min_overall_score:
            return {
                "eligible": False,
                "reason": f"전체 점수 부족: {overall_score:.3f} < {min_overall_score}"
            }
        
        if response_time > max_response_time:
            return {
                "eligible": False,
                "reason": f"응답 시간 초과: {response_time:.3f}초 > {max_response_time}초"
            }
        
        if pass_rate < min_test_pass_rate:
            return {
                "eligible": False,
                "reason": f"테스트 통과율 부족: {pass_rate:.1%} < {min_test_pass_rate:.1%}"
            }
        
        return {"eligible": True, "reason": "배포 조건 만족"}
    
    def _get_current_production_adapter(self) -> Optional[str]:
        """현재 프로덕션 어댑터 이름 조회"""
        if not self.deployment_log:
            return None
        
        # 가장 최근 배포 기록의 어댑터
        return self.deployment_log[-1]["adapter_name"]
    
    def _backup_current_adapter(self, adapter_name: str):
        """현재 어댑터 백업"""
        production_path = self.production_dir / "current"
        if not production_path.exists():
            return
        
        backup_path = self.backup_dir / adapter_name
        if backup_path.exists():
            shutil.rmtree(backup_path)
        
        shutil.copytree(production_path, backup_path)
        logger.debug(f"어댑터 백업 완료: {adapter_name}")
    
    def _cleanup_old_backups(self, days: int = 30) -> List[str]:
        """오래된 백업 정리"""
        cutoff_time = datetime.now() - timedelta(days=days)
        deleted_backups = []
        
        for backup_path in self.backup_dir.iterdir():
            if backup_path.is_dir():
                # 백업 시간 확인 (파일 생성 시간 기준)
                backup_time = datetime.fromtimestamp(backup_path.stat().st_ctime)
                if backup_time < cutoff_time:
                    try:
                        shutil.rmtree(backup_path)
                        deleted_backups.append(backup_path.name)
                        logger.debug(f"오래된 백업 삭제: {backup_path.name}")
                    except Exception as e:
                        logger.warning(f"백업 삭제 실패: {backup_path.name} - {e}")
        
        return deleted_backups
    
    def _load_deployment_log(self) -> List[Dict[str, Any]]:
        """배포 로그 로드"""
        if not self.deployment_log_file.exists():
            return []
        
        try:
            with open(self.deployment_log_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"배포 로그 로드 실패: {e}")
            return []
    
    def _save_deployment_log(self):
        """배포 로그 저장"""
        try:
            with open(self.deployment_log_file, 'w', encoding='utf-8') as f:
                json.dump(self.deployment_log, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"배포 로그 저장 실패: {e}")
    
    def _create_production_metadata(self, deployment_record: Dict[str, Any]):
        """프로덕션 메타데이터 파일 생성"""
        metadata = {
            "adapter_info": deployment_record,
            "created_at": datetime.now().isoformat(),
            "version": "1.0"
        }
        
        metadata_file = self.production_dir / "current" / "production_metadata.json"
        try:
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"프로덕션 메타데이터 생성 실패: {e}")