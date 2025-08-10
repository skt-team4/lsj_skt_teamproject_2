"""
콘텐츠 기반 Funnel (Funnel 2)
검색 쿼리와 메뉴/카테고리 매칭 기반 추천
"""

import json
import logging
from typing import List, Dict, Any, Optional
from collections import Counter
import re

logger = logging.getLogger(__name__)


class ContentFunnel:
    """콘텐츠 기반 후보 생성 Funnel"""
    
    def __init__(self, restaurants_path: str = "data/restaurants_optimized.json"):
        """
        Args:
            restaurants_path: 매장 데이터 파일 경로
        """
        self.restaurants_path = restaurants_path
        self.restaurants = []
        self._load_data()
        self._build_content_index()
    
    def _load_data(self):
        """매장 데이터 로드"""
        try:
            with open(self.restaurants_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.restaurants = data.get('restaurants', [])
            
            logger.info(f"콘텐츠 Funnel: {len(self.restaurants)}개 매장 데이터 로드 완료")
            
        except Exception as e:
            logger.error(f"매장 데이터 로드 실패: {e}")
            self.restaurants = []
    
    def _build_content_index(self):
        """콘텐츠 검색을 위한 인덱스 구축"""
        self.content_index = {}
        
        for restaurant in self.restaurants:
            shop_id = restaurant.get('shopId', '')
            
            # 검색 가능한 모든 텍스트 수집
            searchable_text = []
            
            # 매장명
            shop_name = restaurant.get('shopName', '')
            if shop_name:
                searchable_text.append(shop_name)
            
            # 카테고리
            category = restaurant.get('category', '')
            if category:
                searchable_text.append(category)
            
            # 메뉴명들
            menus = restaurant.get('menus', [])
            for menu in menus:
                menu_name = menu.get('name', '')
                if menu_name:
                    searchable_text.append(menu_name)
            
            # 검색용 텍스트 통합 (소문자 변환)
            combined_text = ' '.join(searchable_text).lower()
            self.content_index[shop_id] = {
                'text': combined_text,
                'tokens': self._tokenize(combined_text),
                'menus': [menu.get('name', '').lower() for menu in menus],
                'category': category.lower()
            }
        
        logger.info(f"콘텐츠 인덱스 구축 완료: {len(self.content_index)}개 매장")
    
    def _tokenize(self, text: str) -> List[str]:
        """텍스트를 토큰으로 분리"""
        # 한글, 영문, 숫자만 추출
        tokens = re.findall(r'[가-힣a-zA-Z0-9]+', text)
        return [token.lower() for token in tokens if len(token) > 1]
    
    def get_candidates(self, 
                      query: Optional[str] = None,
                      filters: Optional[Dict[str, Any]] = None,
                      limit: int = 50) -> List[Dict[str, Any]]:
        """
        콘텐츠 기반 후보 매장 반환
        
        Args:
            query: 검색 쿼리 (메뉴명, 음식 종류 등)
            filters: 추가 필터 조건
            limit: 반환할 후보 수
            
        Returns:
            콘텐츠 매칭도 순으로 정렬된 후보 매장 리스트
        """
        if not query:
            # 쿼리가 없으면 빈 결과 반환
            return []
        
        candidates = []
        query_tokens = self._tokenize(query.lower())
        
        if not query_tokens:
            return []
        
        for restaurant in self.restaurants:
            shop_id = restaurant.get('shopId', '')
            
            # 콘텐츠 매칭 점수 계산
            content_score, match_reasons = self._calculate_content_score(
                shop_id, query_tokens, query.lower()
            )
            
            # 점수가 0이면 건너뛰기
            if content_score <= 0:
                continue
            
            # 기본 필터 적용
            if not self._passes_basic_filters(restaurant, filters or {}):
                continue
            
            candidate = {
                'shop_id': shop_id,
                'shop_name': restaurant.get('shopName', ''),
                'category': restaurant.get('category', ''),
                'funnel_source': 'content',
                'content_score': content_score,
                'reason': self._format_match_reason(match_reasons, query)
            }
            candidates.append(candidate)
        
        # 콘텐츠 점수로 정렬
        candidates.sort(key=lambda x: x['content_score'], reverse=True)
        
        logger.info(f"콘텐츠 Funnel: {len(candidates[:limit])}개 후보 생성 (쿼리: '{query}')")
        return candidates[:limit]
    
    def _calculate_content_score(self, shop_id: str, query_tokens: List[str], query: str) -> tuple[float, List[str]]:
        """콘텐츠 매칭 점수 계산"""
        if shop_id not in self.content_index:
            return 0.0, []
        
        index_data = self.content_index[shop_id]
        score = 0.0
        match_reasons = []
        
        # 1. 정확한 메뉴명 매칭 (최우선, 50점)
        for menu_name in index_data['menus']:
            if query in menu_name or menu_name in query:
                score += 50
                match_reasons.append(f"메뉴 '{menu_name}' 매칭")
                break
        
        # 2. 카테고리 매칭 (30점)
        category = index_data['category']
        if any(token in category for token in query_tokens) or query in category:
            score += 30
            match_reasons.append(f"카테고리 '{category}' 매칭")
        
        # 3. 토큰 기반 부분 매칭 (토큰당 5점, 최대 25점)
        content_tokens = index_data['tokens']
        matched_tokens = []
        
        for query_token in query_tokens:
            for content_token in content_tokens:
                if query_token in content_token or content_token in query_token:
                    if content_token not in matched_tokens:
                        score += 5
                        matched_tokens.append(content_token)
                        break
        
        if matched_tokens:
            # 최대 25점으로 제한
            token_score = min(len(matched_tokens) * 5, 25)
            score = score - len(matched_tokens) * 5 + token_score  # 위에서 더한 것 조정
            if len(matched_tokens) > 1:
                match_reasons.append(f"키워드 {len(matched_tokens)}개 매칭")
        
        # 4. 매장명 매칭 (15점)
        shop_name_tokens = self._tokenize(query)
        for restaurant in self.restaurants:
            if restaurant.get('shopId') == shop_id:
                shop_name = restaurant.get('shopName', '').lower()
                if any(token in shop_name for token in shop_name_tokens) or query in shop_name:
                    score += 15
                    match_reasons.append("매장명 매칭")
                break
        
        return score, match_reasons
    
    def _passes_basic_filters(self, restaurant: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """기본 필터 조건 확인"""
        # 카테고리 필터
        if filters.get('category'):
            category_filter = filters['category'].lower()
            if category_filter not in restaurant.get('category', '').lower():
                return False
        
        # 착한가게 필터
        if filters.get('is_good_influence'):
            if not restaurant.get('attributes', {}).get('isGoodShop', False):
                return False
        
        # 급식카드 필터
        if filters.get('accepts_meal_card'):
            if not restaurant.get('attributes', {}).get('acceptsMealCard', False):
                return False
        
        return True
    
    def _format_match_reason(self, match_reasons: List[str], query: str) -> str:
        """매칭 이유 포맷팅"""
        if not match_reasons:
            return f"'{query}' 관련"
        
        # 중복 제거하고 간소화
        unique_reasons = []
        for reason in match_reasons:
            if reason not in unique_reasons:
                unique_reasons.append(reason)
        
        return ' · '.join(unique_reasons[:3])  # 최대 3개까지만
    
    def get_popular_keywords(self) -> Dict[str, int]:
        """인기 키워드 분석"""
        keyword_counter = Counter()
        
        for shop_id, index_data in self.content_index.items():
            keyword_counter.update(index_data['tokens'])
        
        return dict(keyword_counter.most_common(20))


# 테스트 함수
def test_content_funnel():
    """콘텐츠 Funnel 테스트"""
    funnel = ContentFunnel()
    
    print("=== 콘텐츠 기반 Funnel 테스트 ===")
    
    # 메뉴명 검색
    bibimbap_candidates = funnel.get_candidates(
        query="비빔밥",
        limit=3
    )
    print(f"\n'비빔밥' 검색 결과 Top 3:")
    for i, candidate in enumerate(bibimbap_candidates, 1):
        print(f"{i}. {candidate['shop_name']} ({candidate['category']}) - {candidate['content_score']:.1f}점")
        print(f"   이유: {candidate['reason']}")
    
    # 카테고리 검색
    korean_candidates = funnel.get_candidates(
        query="한식",
        limit=5
    )
    print(f"\n'한식' 검색 결과 Top 5:")
    for i, candidate in enumerate(korean_candidates, 1):
        print(f"{i}. {candidate['shop_name']} - {candidate['content_score']:.1f}점")
        print(f"   이유: {candidate['reason']}")
    
    # 복합 키워드 검색
    chicken_candidates = funnel.get_candidates(
        query="치킨 매운",
        limit=3
    )
    print(f"\n'치킨 매운' 검색 결과 Top 3:")
    for i, candidate in enumerate(chicken_candidates, 1):
        print(f"{i}. {candidate['shop_name']} - {candidate['content_score']:.1f}점")
        print(f"   이유: {candidate['reason']}")
    
    # 인기 키워드
    popular_keywords = funnel.get_popular_keywords()
    print(f"\n=== 인기 키워드 Top 10 ===")
    for i, (keyword, count) in enumerate(list(popular_keywords.items())[:10], 1):
        print(f"{i}. {keyword} ({count}회)")


if __name__ == "__main__":
    test_content_funnel()