// services/apiService_openai_compatible.ts
// OpenAI API와 100% 호환되는 버전 - API 키만 바꾸면 작동

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

// OpenAI API 설정 (워크스테이션 서버로 대체 가능)
const API_CONFIG = {
  openai: {
    // 옵션 1: 워크스테이션 AI 서버 (OpenAI 호환)
    baseUrl: process.env.EXPO_PUBLIC_OPENAI_BASE_URL || 'https://your-workstation.ngrok.io/v1/chat/completions',
    apiKey: process.env.EXPO_PUBLIC_OPENAI_API_KEY || 'sk-workstation-123456789',
    
    // 옵션 2: 실제 OpenAI API 사용
    // baseUrl: 'https://api.openai.com/v1/chat/completions',
    // apiKey: 'sk-your-real-openai-api-key',
    
    model: 'gpt-3.5-turbo',
  },
  timeout: 15000,
};

// 카테고리별 시스템 프롬프트 생성
const getCategoryPrompt = (category?: MealCategory) => {
  const basePrompt = `당신은 "얌이"라는 이름의 친근하고 귀여운 음식 추천 및 길 안내 AI입니다. 
어린이들이 좋아할 만한 톤으로 대화합니다.
응답은 한국어로 하며, 200자 이내로 간결하게 답변해주세요.
이모지를 적절히 사용해서 친근하게 답변해주세요.`;

  const categoryPrompts = {
    distance: `${basePrompt}\n지금은 "거리/접근성" 관련 급식 추천을 요청받았습니다. 현재 위치 주변에서 먹을 수 있는 메뉴를 추천해주세요.`,
    cost: `${basePrompt}\n지금은 "가격/영양" 관련 음식 추천을 요청받았습니다. 경제적이면서도 영양가 높은 메뉴를 추천해주세요.`,
    preference: `${basePrompt}\n지금은 "선호도" 관련 급식 추천을 요청받았습니다. 평소에 뭐 좋아하는지 물어보고 그에 맞는 음식 및 음식점 추천해주세요.`,
    allergy: `${basePrompt}\n지금은 "알레르기" 관련 정보를 요청받았습니다. 사용자의 알레르기 정보를 물어보고 안전한 식사에 대해 안내해주세요.`
  };

  return category ? categoryPrompts[category] : basePrompt;
};

// OpenAI API 또는 워크스테이션 서버를 통한 챗봇 메시지 전송
export async function sendChatMessage(message: string, category?: MealCategory): Promise<ApiResponse> {
  try {
    console.log('API 호출:', API_CONFIG.openai.baseUrl);
    
    const response = await fetch(API_CONFIG.openai.baseUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${API_CONFIG.openai.apiKey}`,
      },
      body: JSON.stringify({
        model: API_CONFIG.openai.model,
        messages: [
          {
            role: 'system',
            content: getCategoryPrompt(category)
          },
          {
            role: 'user',
            content: message.trim()
          }
        ],
        max_tokens: 300,
        temperature: 0.8,
        presence_penalty: 0.1,
        frequency_penalty: 0.1,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      console.error('API 에러:', response.status, errorData);
      throw new Error(`API error: ${response.status} - ${errorData.error?.message || 'Unknown error'}`);
    }

    const data = await response.json();
    console.log('API 응답:', data);
    
    if (!data.choices || !data.choices[0] || !data.choices[0].message) {
      throw new Error('Invalid response format');
    }

    return {
      success: true,
      message: data.choices[0].message.content.trim(),
      data: {
        category: category,
        usage: data.usage,
      }
    };
  } catch (error) {
    console.error('API 호출 오류:', error);
    
    // API 키 관련 오류 체크
    if (error instanceof Error && error.message.includes('401')) {
      return {
        success: false,
        message: '⚠️ API 키 설정을 확인해주세요.',
        error: 'Invalid API key',
      };
    }
    
    // 네트워크 오류
    if (error instanceof TypeError && error.message.includes('fetch')) {
      return {
        success: false,
        message: '📡 서버 연결을 확인해주세요.',
        error: 'Network error',
      };
    }

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

// 카테고리별 추천
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

// 서비스 상태 확인
export async function checkServiceHealth(): Promise<boolean> {
  try {
    const baseUrl = API_CONFIG.openai.baseUrl.replace('/v1/chat/completions', '');
    const response = await fetch(`${baseUrl}/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(5000),
    });
    
    return response.ok;
  } catch (error) {
    console.error('헬스체크 실패:', error);
    return false;
  }
}