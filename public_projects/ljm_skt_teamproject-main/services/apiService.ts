// services/apiService.ts
export type MealCategory = 'distance' | 'cost' | 'preference' | 'allergy';

export type ApiResponse = {
  success: boolean;
  message: string;
  data?: {
    recommendations?: any[];
    category?: string;
    usage?: any;
  };
  error?: string;
};

export type Message = {
  id: string;
  text: string;
  isUser: boolean;
  timestamp: Date;
  category?: string;
};

// API 설정 - Cloud Run 서비스로 변경
const API_CONFIG = {
  // 기존 OpenAI API 대신 배포된 Cloud Run 서비스 사용
  nabiyam: {
    // 실제 배포된 서비스 URL들
    services: {
      primary: 'https://nabiyam-chatbot-web-816056347823.asia-northeast3.run.app',
      secondary: 'https://nabiyam-webapp-v2-816056347823.asia-northeast3.run.app',
      // 워크스테이션 서버 (ngrok URL - 필요시 업데이트)
      workstation: process.env.EXPO_PUBLIC_WORKSTATION_URL || '',
    },
    // 활성 서비스 선택 (primary, secondary, workstation)
    activeService: 'primary',
  },
  timeout: 15000, // 15초 타임아웃
};

// 현재 활성 API URL 가져오기
const getActiveApiUrl = () => {
  const { nabiyam } = API_CONFIG;
  const service = nabiyam.services[nabiyam.activeService as keyof typeof nabiyam.services];
  
  // 환경변수로 URL 오버라이드 가능
  if (process.env.EXPO_PUBLIC_API_URL) {
    return process.env.EXPO_PUBLIC_API_URL;
  }
  
  return service || nabiyam.services.primary;
};

// 카테고리별 시스템 프롬프트 생성 (백엔드로 전달용)
const getCategoryContext = (category?: MealCategory) => {
  const categoryContexts = {
    distance: '거리/접근성을 고려한 음식 추천',
    cost: '가격/영양을 고려한 경제적인 음식 추천',
    preference: '아이들의 선호도를 고려한 인기 메뉴 추천',
    allergy: '알레르기 정보를 고려한 안전한 식사 추천'
  };

  return category ? categoryContexts[category] : '일반 음식 추천';
};

// Cloud Run 서비스를 통한 챗봇 메시지 전송
export async function sendChatMessage(message: string, category?: MealCategory): Promise<ApiResponse> {
  try {
    const apiUrl = getActiveApiUrl();
    console.log('API 호출:', apiUrl);

    // Cloud Run 서비스의 /chat 엔드포인트 호출
    const response = await fetch(`${apiUrl}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // 필요시 인증 헤더 추가
        // 'Authorization': `Bearer ${API_TOKEN}`,
      },
      body: JSON.stringify({
        message: message.trim(),
        user_id: 'mobile_user', // 나중에 실제 사용자 ID로 변경
        session_id: `session_${Date.now()}`, // 세션 관리
        context: getCategoryContext(category),
        category: category,
      }),
    });

    if (!response.ok) {
      // 에러 응답 처리
      const errorData = await response.json().catch(() => ({}));
      console.error('API 에러:', response.status, errorData);
      
      // 백엔드 서비스가 다운된 경우 폴백
      if (response.status === 503 || response.status === 502) {
        return {
          success: false,
          message: '🔧 서버 점검 중이에요. 잠시만 기다려주세요!',
          error: 'Service unavailable',
        };
      }
      
      throw new Error(`API error: ${response.status}`);
    }

    const data = await response.json();
    console.log('API 응답:', data);
    
    // Cloud Run 서비스 응답 형식에 맞게 파싱
    if (data.response || data.message) {
      return {
        success: true,
        message: data.response || data.message,
        data: {
          category: category,
          recommendations: data.recommendations || [],
          // 추가 데이터가 있으면 여기에 포함
        }
      };
    }

    // 예상치 못한 응답 형식
    throw new Error('Invalid response format from server');
    
  } catch (error) {
    console.error('API 호출 오류:', error);
    
    // 네트워크 오류
    if (error instanceof TypeError && error.message.includes('fetch')) {
      return {
        success: false,
        message: '📡 인터넷 연결을 확인해주세요.',
        error: 'Network error',
      };
    }
    
    // 타임아웃
    if (error instanceof Error && error.message.includes('timeout')) {
      return {
        success: false,
        message: '⏱️ 응답 시간이 초과되었어요. 다시 시도해주세요.',
        error: 'Timeout',
      };
    }

    // 기본 오류 메시지
    return {
      success: false,
      message: '죄송해요, 일시적으로 응답할 수 없어요. 잠시 후 다시 시도해 주세요. 🥺',
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

// 카테고리별 추천 메시지
const categoryQuestions = {
  distance: '학교 근처에서 쉽게 구할 수 있는 재료로 만든 오늘의 급식 메뉴를 추천해주세요',
  cost: '경제적이면서도 영양가 높은 급식 메뉴를 추천해주세요',
  preference: '아이들이 가장 좋아하는 인기 급식 메뉴를 추천해주세요',
  allergy: '급식의 알레르기 주의사항과 안전한 식사 방법에 대해 알려주세요'
};

// Cloud Run 서비스를 통한 카테고리별 추천
export async function getCategoryRecommendation(category: MealCategory): Promise<ApiResponse> {
  try {
    return await sendChatMessage(categoryQuestions[category], category);
  } catch (error) {
    console.error('카테고리 추천 오류:', error);
    return {
      success: false,
      message: '추천 메뉴를 불러오는 중 오류가 발생했어요. 다시 시도해 주세요. 😅',
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

// 서비스 상태 확인 (헬스체크)
export async function checkServiceHealth(): Promise<boolean> {
  try {
    const apiUrl = getActiveApiUrl();
    const response = await fetch(`${apiUrl}/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(5000), // 5초 타임아웃
    });
    
    return response.ok;
  } catch (error) {
    console.error('헬스체크 실패:', error);
    return false;
  }
}

// API 서비스 전환 (필요시 사용)
export function switchApiService(service: 'primary' | 'secondary' | 'workstation') {
  API_CONFIG.nabiyam.activeService = service;
  console.log(`API 서비스 전환: ${service}`);
}