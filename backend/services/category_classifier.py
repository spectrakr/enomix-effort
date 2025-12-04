"""
카테고리 자동 분류 모듈
"""
import logging
from typing import Dict, List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
import json
import os

logger = logging.getLogger(__name__)

class CategoryClassifier:
    """카테고리 자동 분류기"""
    
    def __init__(self):
        self.model = None
        self.vectorizer = None
        self.categories = []
        self.is_trained = False
        
    def load_training_data(self) -> List[Tuple[str, str]]:
        """학습 데이터 로드 (기존 카테고리 데이터 사용)"""
        try:
            # 카테고리 파일 로드
            categories_file = os.path.join(
                os.path.dirname(__file__), '..', '..', 'data', 'docs', 'categories.json'
            )
            
            if not os.path.exists(categories_file):
                logger.warning("카테고리 파일을 찾을 수 없습니다")
                return []
            
            with open(categories_file, 'r', encoding='utf-8') as f:
                categories = json.load(f)
            
            # 공수 산정 데이터 로드
            effort_file = os.path.join(
                os.path.dirname(__file__), '..', '..', 'data', 'docs', 'effort_estimations.json'
            )
            
            if not os.path.exists(effort_file):
                logger.warning("공수 산정 파일을 찾을 수 없습니다")
                return []
            
            with open(effort_file, 'r', encoding='utf-8') as f:
                effort_data = json.load(f)
            
            # 학습 데이터 생성 (카테고리 정보 + 공수 산정 텍스트)
            training_data = []
            
            for category_group, items in categories.items():
                for sub_category, features in items.items():
                    if isinstance(features, list):
                        for feature in features:
                            # 카테고리와 기능명을 학습 데이터로 사용
                            category_label = f"{category_group} > {sub_category} > {feature}"
                            training_data.append((feature, category_label))
            
            # 공수 산정 데이터에서도 학습 데이터 추출
            for item in effort_data:
                # 카테고리 정보가 있는 경우에만 추가
                major = item.get('major_category')
                minor = item.get('minor_category')
                sub = item.get('sub_category')
                
                if major and minor and sub:
                    # 카테고리 레이블 생성
                    category_label = f"{major} > {minor} > {sub}"
                    
                    # 제목과 설명을 결합하여 학습 데이터로 사용
                    text_parts = []
                    if item.get('title'):
                        text_parts.append(str(item['title']))
                    if item.get('notes'):
                        text_parts.append(str(item['notes']))
                    
                    # description이 딕셔너리인 경우 처리
                    description = item.get('description')
                    if description:
                        if isinstance(description, dict):
                            # 딕셔너리인 경우 텍스트 추출
                            if 'content' in description:
                                text_parts.append(str(description.get('content', '')))
                        else:
                            text_parts.append(str(description))
                    
                    if text_parts:
                        training_text = ' '.join(text_parts)
                        training_data.append((training_text, category_label))
            
            logger.info(f"학습 데이터 로드 완료: {len(training_data)}개")
            return training_data
            
        except Exception as e:
            logger.error(f"학습 데이터 로드 오류: {e}")
            return []
    
    def train(self, training_data: List[Tuple[str, str]]):
        """모델 학습"""
        try:
            if not training_data:
                logger.warning("학습 데이터가 없습니다")
                return False
            
            # 텍스트와 레이블 분리
            texts, labels = zip(*training_data)
            
            # 모델 생성 및 학습 (학습 데이터가 적을 때 더 강한 정규화)
            self.model = Pipeline([
                ('tfidf', TfidfVectorizer(
                    max_features=500,  # 특성 수 감소
                    ngram_range=(1, 2),  # n-gram 범위 축소
                    min_df=2,  # 최소 문서 빈도 증가
                    max_df=0.95,  # 최대 문서 빈도
                    stop_words=None  # 불용어 제거하지 않음 (한국어)
                )),
                ('clf', MultinomialNB(alpha=1.0))  # 더 강한 라플라스 스무딩
            ])
            
            self.model.fit(texts, labels)
            self.is_trained = True
            
            logger.info(f"모델 학습 완료: {len(texts)}개 샘플")
            return True
            
        except Exception as e:
            logger.error(f"모델 학습 오류: {e}")
            return False
    
    def predict(self, text: str) -> str:
        """카테고리 예측"""
        try:
            if not self.is_trained or self.model is None:
                logger.warning("모델이 학습되지 않았습니다")
                return None
            
            predicted = self.model.predict([text])[0]
            probability = self.model.predict_proba([text])[0].max()
            
            logger.info(f"예측 결과: {predicted} (신뢰도: {float(probability):.2f})")
            return predicted
            
        except Exception as e:
            logger.error(f"예측 오류: {e}")
            return None
    
    def get_confidence(self, text: str) -> float:
        """예측 신뢰도 반환"""
        try:
            if not self.is_trained or self.model is None:
                return 0.0
            
            probability = self.model.predict_proba([text])[0].max()
            return float(probability)
            
        except Exception as e:
            logger.error(f"신뢰도 계산 오류: {e}")
            return 0.0
    
    def initialize(self):
        """초기화 및 자동 학습"""
        try:
            training_data = self.load_training_data()
            if training_data:
                self.train(training_data)
                logger.info("카테고리 분류기 초기화 완료")
            else:
                logger.warning("학습 데이터가 없어 초기화 실패")
                
        except Exception as e:
            logger.error(f"분류기 초기화 오류: {e}")

# 전역 인스턴스
classifier = CategoryClassifier()

def auto_classify(text: str) -> Tuple[str, float]:
    """자동 카테고리 분류"""
    try:
        if not classifier.is_trained:
            classifier.initialize()
        
        if not classifier.is_trained:
            return None, 0.0
        
        # predict_proba를 한 번만 호출하여 예측과 신뢰도를 동시에 가져오기
        probabilities = classifier.model.predict_proba([text])[0]
        predicted_index = probabilities.argmax()
        confidence = float(probabilities[predicted_index])
        category = classifier.model.classes_[predicted_index]
        
        logger.info(f"자동 분류 결과: {category} (신뢰도: {confidence:.2f})")
        
        return category, confidence
        
    except Exception as e:
        logger.error(f"자동 분류 오류: {e}")
        return None, 0.0
