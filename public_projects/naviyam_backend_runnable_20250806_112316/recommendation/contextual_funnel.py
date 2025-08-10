"""
상황/규칙 기반 Funnel (Funnel 3)
시간대, 위치, 영업시간 등 컨텍스트 기반 추천
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, time
import math

logger = logging.getLogger(__name__)


class ContextualFunnel:
    """상황/규칙 기반 후보 생성 Funnel"""
    
    def __init__(self, restaurants_path: str = "data/restaurants_optimized.json"):
        """
        Args:
            restaurants_path: 매장 데이터 파일 경로
        """
        self.restaurants_path = restaurants_path
        self.restaurants = []
        self._load_data()
    
    def _load_data(self):
        """매장 데이터 로드"""
        try:
            with open(self.restaurants_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.restaurants = data.get('restaurants', [])
            
            logger.info(f"상황 Funnel: {len(self.restaurants)}개 매장 데이터 로드 완료")
            
        except Exception as e:
            logger.error(f"매장 데이터 로드 실패: {e}")
            self.restaurants = []
    
    def get_candidates(self, 
                      user_location: Optional[str] = None,
                      current_time: Optional[datetime] = None,
                      time_of_day: Optional[str] = None,
                      filters: Optional[Dict[str, Any]] = None,
                      limit: int = 30) -> List[Dict[str, Any]]:
        """
        상황 기반 후보 매장 반환
        
        Args:
            user_location: 사용자 위치 (구 단위, 예: "관악구")
            current_time: 현재 시간 
            time_of_day: 시간대 ("breakfast", "lunch", "dinner", "snack")
            filters: 추가 필터 조건
            limit: 반환할 후보 수
            
        Returns:
            상황에 맞는 후보 매장 리스트
        """
        if current_time is None:
            current_time = datetime.now()
        
        candidates = []
        
        for restaurant in self.restaurants:
            # 컨텍스트 점수 계산
            context_score = self._calculate_context_score(
                restaurant, user_location, current_time, time_of_day
            )
            
            # 기본 필터 적용
            if not self._passes_basic_filters(restaurant, filters or {}):
                continue
            
            shop_id = restaurant.get('shopId', '')
            candidate = {
                'shop_id': shop_id,
                'shop_name': restaurant.get('shopName', ''),
                'category': restaurant.get('category', ''),
                'funnel_source': 'contextual',
                'context_score': context_score,
                'reason': self._get_context_reason(
                    restaurant, user_location, current_time, time_of_day
                )
            }
            candidates.append(candidate)
        
        # 컨텍스트 점수로 정렬
        candidates.sort(key=lambda x: x['context_score'], reverse=True)
        
        logger.info(f"상황 Funnel: {len(candidates[:limit])}개 후보 생성 (위치: {user_location}, 시간: {time_of_day})")
        return candidates[:limit]
    
    def _calculate_context_score(self, 
                                restaurant: Dict[str, Any],
                                user_location: Optional[str],
                                current_time: datetime,
                                time_of_day: Optional[str]) -> float:
        """상황 기반 점수 계산"""
        score = 0.0
        
        # 1. 위치 기반 점수 (최대 40점)
        if user_location:
            location_score = self._get_location_score(restaurant, user_location)
            score += location_score
        
        # 2. 영업시간 기반 점수 (최대 30점)
        operating_score = self._get_operating_score(restaurant, current_time)
        score += operating_score
        
        # 3. 시간대 기반 점수 (최대 30점)
        if time_of_day:
            time_score = self._get_time_of_day_score(restaurant, time_of_day)
            score += time_score
        
        return score
    
    def _get_location_score(self, restaurant: Dict[str, Any], user_location: str) -> float:
        """위치 기반 점수 계산"""
        address = restaurant.get('location', {}).get('address', '')
        
        # 같은 구에 있으면 높은 점수
        if user_location in address:
            return 40.0
        
        # 서울 지역이면 중간 점수
        if '서울' in address:
            return 20.0
        
        # 경기도면 낮은 점수
        if '경기' in address:
            return 10.0
        
        return 5.0  # 기본 점수
    
    def _get_operating_score(self, restaurant: Dict[str, Any], current_time: datetime) -> float:
        """영업시간 기반 점수 계산"""
        hours = restaurant.get('hours', {})
        open_time_str = hours.get('open')
        close_time_str = hours.get('close')
        
        if not (open_time_str and close_time_str):
            return 10.0  # 정보 없으면 기본 점수
        
        try:
            current_time_only = current_time.time()
            open_time = datetime.strptime(open_time_str, '%H:%M').time()
            close_time = datetime.strptime(close_time_str, '%H:%M').time()
            
            # 현재 영업 중이면 높은 점수
            if self._is_open_now(current_time_only, open_time, close_time):
                return 30.0
            
            # 곧 열 예정이면 중간 점수 (1시간 이내)
            if self._opens_soon(current_time_only, open_time):
                return 15.0
            
            return 5.0  # 영업시간 외
            
        except ValueError:
            return 10.0  # 시간 파싱 실패
    
    def _is_open_now(self, current_time: time, open_time: time, close_time: time) -> bool:
        """현재 영업 중인지 확인"""
        if close_time < open_time:  # 자정 넘어서 영업 (예: 22:00 - 02:00)
            return current_time >= open_time or current_time <= close_time
        else:  # 일반적인 경우
            return open_time <= current_time <= close_time
    
    def _opens_soon(self, current_time: time, open_time: time) -> bool:
        """1시간 이내에 열 예정인지 확인"""
        current_minutes = current_time.hour * 60 + current_time.minute
        open_minutes = open_time.hour * 60 + open_time.minute
        
        # 1시간(60분) 이내에 열 예정
        time_diff = (open_minutes - current_minutes) % (24 * 60)
        return 0 < time_diff <= 60
    
    def _get_time_of_day_score(self, restaurant: Dict[str, Any], time_of_day: str) -> float:
        """시간대 기반 점수 계산"""
        category = restaurant.get('category', '').lower()
        
        # 시간대별 카테고리 선호도
        time_category_preferences = {
            'breakfast': {
                '카페': 30, '기타/디저트': 25, '베이커리': 30,
                '한식': 15, '분식': 20
            },
            'lunch': {
                '한식': 30, '중식': 25, '일식': 25, '분식': 20,
                '양식': 20, '치킨': 15
            },
            'dinner': {
                '한식': 25, '중식': 25, '일식': 25, '양식': 30,
                '치킨': 30, '고기': 30, '분식': 15
            },
            'snack': {
                '카페': 30, '기타/디저트': 30, '치킨': 25,
                '분식': 25, '베이커리': 20
            }
        }
        
        preferences = time_category_preferences.get(time_of_day, {})
        
        # 카테고리 매칭으로 점수 계산
        for cat_keyword, score in preferences.items():
            if cat_keyword in category:
                return float(score)
        
        return 10.0  # 기본 점수
    
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
        
        return True
    
    def _get_context_reason(self, 
                           restaurant: Dict[str, Any],
                           user_location: Optional[str],
                           current_time: datetime,
                           time_of_day: Optional[str]) -> str:
        """상황 기반 추천 이유 생성"""
        reasons = []
        
        # 위치 이유
        if user_location:
            address = restaurant.get('location', {}).get('address', '')
            if user_location in address:
                reasons.append(f'{user_location} 근처')
        
        # 영업시간 이유
        hours = restaurant.get('hours', {})
        if hours.get('open') and hours.get('close'):
            try:
                current_time_only = current_time.time()
                open_time = datetime.strptime(hours['open'], '%H:%M').time()
                close_time = datetime.strptime(hours['close'], '%H:%M').time()
                
                if self._is_open_now(current_time_only, open_time, close_time):
                    reasons.append('현재 영업중')
                elif self._opens_soon(current_time_only, open_time):
                    reasons.append('곧 영업 시작')
            except:
                pass
        
        # 시간대 이유
        if time_of_day:
            category = restaurant.get('category', '').lower()
            time_reasons = {
                'breakfast': '아침 추천',
                'lunch': '점심 추천', 
                'dinner': '저녁 추천',
                'snack': '간식 추천'
            }
            if time_of_day in time_reasons:
                reasons.append(time_reasons[time_of_day])
        
        return ' · '.join(reasons) if reasons else '상황 맞춤'


# 테스트 함수
def test_contextual_funnel():
    """상황 Funnel 테스트"""
    funnel = ContextualFunnel()
    
    print("=== 상황/규칙 기반 Funnel 테스트 ===")
    
    # 점심시간 관악구 근처 추천
    lunch_candidates = funnel.get_candidates(
        user_location="관악구",
        time_of_day="lunch",
        limit=5
    )
    print(f"\n점심시간 관악구 근처 추천 Top 5:")
    for i, candidate in enumerate(lunch_candidates, 1):
        print(f"{i}. {candidate['shop_name']} ({candidate['category']}) - {candidate['context_score']:.1f}점")
        print(f"   이유: {candidate['reason']}")
    
    # 저녁시간 전체 지역 추천
    dinner_candidates = funnel.get_candidates(
        time_of_day="dinner",
        limit=3
    )
    print(f"\n저녁시간 추천 Top 3:")
    for i, candidate in enumerate(dinner_candidates, 1):
        print(f"{i}. {candidate['shop_name']} ({candidate['category']}) - {candidate['context_score']:.1f}점")
        print(f"   이유: {candidate['reason']}")
    
    # 현재 시간 기준 영업중인 곳
    current_time = datetime.now().replace(hour=14, minute=30)  # 오후 2시 30분으로 가정
    open_candidates = funnel.get_candidates(
        current_time=current_time,
        limit=3
    )
    print(f"\n오후 2시 30분 영업중인 곳 Top 3:")
    for i, candidate in enumerate(open_candidates, 1):
        print(f"{i}. {candidate['shop_name']} - {candidate['context_score']:.1f}점")
        print(f"   이유: {candidate['reason']}")


if __name__ == "__main__":
    test_contextual_funnel()