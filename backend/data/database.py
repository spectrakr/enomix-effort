from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_core.documents import Document
import os
import re
import logging
import json
from datetime import datetime
from ..utils.config import CHROMA_DIR, DOCS_DIR

logger = logging.getLogger(__name__)

def get_vectordb():
    try:
        embedding = OpenAIEmbeddings()
        vectordb = Chroma(persist_directory=CHROMA_DIR, embedding_function=embedding)
        
        # effort_estimations.json이 벡터 DB에 있는지 확인
        try:
            collection = vectordb.get()
            has_effort_data = False
            
            if collection and "metadatas" in collection:
                for metadata in collection["metadatas"]:
                    if isinstance(metadata, dict) and metadata.get("source") == "effort_estimations.json":
                        has_effort_data = True
                        break
            
            # effort_estimations.json이 없으면 자동으로 인덱싱
            if not has_effort_data:
                json_file_path = os.path.join(DOCS_DIR, "effort_estimations.json")
                if os.path.exists(json_file_path):
                    logger.info("🔄 effort_estimations.json 자동 인덱싱 시작")
                    try:
                        if index_json_data(json_file_path, force=True):
                            logger.info("✅ effort_estimations.json 자동 인덱싱 완료")
                        else:
                            logger.error("❌ effort_estimations.json 자동 인덱싱 실패")
                    except Exception as idx_error:
                        logger.error(f"❌ effort_estimations.json 자동 인덱싱 중 오류: {idx_error}")
        except Exception as coll_error:
            logger.warning(f"⚠️ 벡터 DB 컬렉션 확인 중 오류 (무시하고 계속): {coll_error}")
        
        return vectordb
    except Exception as e:
        logger.error(f"❌ 벡터 데이터베이스 초기화 실패: {e}")
        return None

def get_file_metadata(file_path: str):
    """Get file metadata including last modification time"""
    return {
        "source": os.path.basename(file_path),
        "last_modified": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
        "file_size": os.path.getsize(file_path)
    }

def is_file_modified(file_path: str, vectordb) -> bool:
    """Check if file needs to be reindexed by comparing modification times"""
    try:
        current_metadata = get_file_metadata(file_path)
        collection = vectordb.get()
        
        for metadata in collection["metadatas"]:
            if (isinstance(metadata, dict) and 
                metadata.get("source") == current_metadata["source"]):
                # If file exists in index, check if it's been modified
                if (metadata.get("last_modified") == current_metadata["last_modified"] and
                    metadata.get("file_size") == current_metadata["file_size"]):
                    return False
                return True
        
        # File not found in index
        return True
    except Exception as e:
        logger.error(f"Error checking file modification: {str(e)}")
        return True

def index_document(file_path: str, file_type: str = "pdf", force: bool = False):
    try:
        vectordb = get_vectordb()
        
        # Skip if file is already indexed and hasn't been modified
        if not force and not is_file_modified(file_path, vectordb):
            logger.info(f"📝 Skipping unchanged file: {file_path}")
            return True

        # Remove existing documents for this file if any
        collection = vectordb.get()
        docs_to_remove = []
        for i, metadata in enumerate(collection["metadatas"]):
            if isinstance(metadata, dict) and metadata.get("source") == os.path.basename(file_path):
                docs_to_remove.append(collection["ids"][i])
        
        if docs_to_remove:
            vectordb._collection.delete(docs_to_remove)
            logger.info(f"🗑️ Removed old version of: {file_path}")

        # Load and process the document
        if file_type == "pdf":
            loader = PyMuPDFLoader(file_path)
            documents = loader.load()
        else:  # txt
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            documents = [Document(page_content=content)]

        # Add metadata to all documents
        file_metadata = get_file_metadata(file_path)
        for doc in documents:
            doc.metadata.update(file_metadata)

        # effort_estimations.txt의 경우 티켓별로 분할
        if os.path.basename(file_path) == "effort_estimations.txt":
            # 티켓별로 분할
            docs = []
            content = documents[0].page_content
            tickets = content.split('---\n\n')
            
            for i, ticket in enumerate(tickets):
                if ticket.strip():  # 빈 티켓 제외
                    # 각 티켓을 별도 문서로 생성
                    doc = Document(
                        page_content=ticket.strip(),
                        metadata=documents[0].metadata.copy()
                    )
                    doc.metadata["ticket_index"] = i
                    docs.append(doc)
        else:
            # 다른 파일은 기존 방식 사용
            splitter = CharacterTextSplitter(chunk_size=1200, chunk_overlap=120)
            docs = splitter.split_documents(documents)

        # ✅ 전처리 함수 적용
        for idx, doc in enumerate(docs):
            doc.page_content = doc.page_content  # <-- 이 부분!
            doc.metadata["chunk_index"] = idx

        logger.info(f"📊 총 {len(docs)}개 문서를 처리합니다")
        
        # Process documents in smaller batches (더 작은 배치 크기 사용)
        BATCH_SIZE = 10  # 100에서 10으로 줄임
        total_added = 0
        for i in range(0, len(docs), BATCH_SIZE):
            batch = docs[i:i + BATCH_SIZE]
            vectordb.add_documents(batch)
            vectordb.persist()
            total_added += len(batch)
            logger.info(f"✅ Processed batch {i//BATCH_SIZE + 1} of {(len(docs)-1)//BATCH_SIZE + 1} (총 {total_added}개 문서 추가됨)")
        
        logger.info(f"✅ Document indexed successfully: {file_path} (총 {total_added}개 문서 저장됨)")
        return True
    except Exception as e:
        logger.error(f"❌ Error indexing document: {str(e)}")
        return False

def get_indexed_files():
    try:
        vectordb = get_vectordb()
        collection = vectordb.get()
        sources = set()
        
        for metadata in collection["metadatas"]:
            if isinstance(metadata, dict) and "source" in metadata:
                sources.add(metadata["source"])
                
        return list(sources)
    except Exception as e:
        logger.error(f"❌ Error getting indexed files: {str(e)}")
        return []

def remove_document(file_path: str):
    """Remove document from Chroma DB and delete the file"""
    try:
        vectordb = get_vectordb()
        filename = os.path.basename(file_path)
        
        # Remove from Chroma DB
        collection = vectordb.get()
        docs_to_remove = []
        for i, metadata in enumerate(collection["metadatas"]):
            if isinstance(metadata, dict) and metadata.get("source") == filename:
                docs_to_remove.append(collection["ids"][i])
        
        if docs_to_remove:
            vectordb._collection.delete(docs_to_remove)
            vectordb.persist()
            logger.info(f"🗑️ Removed document from Chroma DB: {filename}")
        
        # Delete the file
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"🗑️ Deleted file: {file_path}")
            return True
        else:
            logger.warning(f"⚠️ File not found: {file_path}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error removing document: {str(e)}")
        return False

def reset_vectordb():
    """
    ✅ Chroma DB의 모든 문서를 안전하게 제거합니다.
    ✅ embedding 호출 없이, 단순히 저장된 문서 ID 기준으로 삭제합니다.
    """
    try:
        vectordb = get_vectordb()
        collection = vectordb.get()

        all_ids = collection.get("ids", [])
        if all_ids:
            BATCH_SIZE = 100  # 안전을 위해 삭제도 batch 처리 가능
            for i in range(0, len(all_ids), BATCH_SIZE):
                batch_ids = all_ids[i:i + BATCH_SIZE]
                vectordb._collection.delete(batch_ids)
            vectordb.persist()
            logger.info(f"✅ Successfully reset Chroma DB - {len(all_ids)}개 문서 삭제 완료")
        else:
            logger.info("ℹ️ Chroma DB에 삭제할 문서가 없습니다.")
        return True

    except Exception as e:
        logger.error(f"❌ Error resetting Chroma DB: {str(e)}")
        return False

def clean_chunk_text(text: str) -> str:
    text = re.sub(r"[^\w\s가-힣.,:;!?()\\[\\]<>/@&%\"'\-]", "", text)
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)

    # ✅ 페이지 번호 제거 (예: "Page 1", "1 / 27", "15페이지" 등)
    text = re.sub(r"^\s*\d+\s*/\s*\d+\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*Page\s+\d+\s*$", "", text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"\d+페이지", "", text)
    return text.strip()

def save_feedback_to_file(feedback_data):
    """피드백 데이터를 파일에 저장 (긍정/부정 모두 지원)
    
    중복 체크 로직:
    - 질문-답변 해시로 동일 세트 판별
    - 같은 질문-답변 세트면 피드백 카운트만 증가
    - 같은 질문이지만 답변이 다르면 최신 답변으로 업데이트
    
    Returns:
        dict: {"saved": bool, "is_new": bool, "feedback_count": int}
            - saved: 저장 성공 여부
            - is_new: 새로운 질문-답변 세트인지
            - feedback_count: 해당 질문-답변 세트의 총 피드백 수
    """
    import hashlib
    
    try:
        feedback_type = feedback_data.get("feedback_type", "positive")
        
        # 피드백 타입에 따라 파일 선택
        if feedback_type == "positive":
            feedback_file = os.path.join(DOCS_DIR, "positive_feedback.json")
            opposite_file = os.path.join(DOCS_DIR, "negative_feedback.json")
        else:
            feedback_file = os.path.join(DOCS_DIR, "negative_feedback.json")
            opposite_file = os.path.join(DOCS_DIR, "positive_feedback.json")
        
        # DOCS_DIR 디렉토리가 없으면 생성
        os.makedirs(DOCS_DIR, exist_ok=True)
        logger.info(f"📁 DOCS_DIR 확인: {DOCS_DIR} (존재: {os.path.exists(DOCS_DIR)})")
        
        # 기존 데이터 로드 (파일이 없으면 빈 리스트로 시작)
        logger.info(f"📄 피드백 파일 확인: {feedback_file} (존재: {os.path.exists(feedback_file)})")
        if os.path.exists(feedback_file):
            try:
                with open(feedback_file, 'r', encoding='utf-8') as f:
                    feedbacks = json.load(f)
                # 파일이 비어있거나 리스트가 아닌 경우 빈 리스트로 초기화
                if not isinstance(feedbacks, list):
                    logger.warning(f"⚠️ 피드백 파일이 리스트 형식이 아님, 빈 리스트로 초기화")
                    feedbacks = []
                logger.info(f"📊 기존 피드백 로드: {len(feedbacks)}개")
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"⚠️ 피드백 파일 읽기 오류: {e}, 빈 리스트로 시작")
                feedbacks = []
        else:
            feedbacks = []
            logger.info(f"📝 새로운 피드백 파일 생성 예정: {feedback_file}")
        
        question = feedback_data["question"]
        answer = feedback_data.get("answer", "")
        
        # 질문-답변 해시 생성 (중복 체크용)
        qa_hash = hashlib.md5(f"{question}|||{answer}".encode('utf-8')).hexdigest()
        
        # 부정 피드백 저장 시: 항상 긍정 피드백 파일 확인 및 제거 (opposite_index에 의존하지 않음)
        if feedback_type == "negative":
            positive_file_path = os.path.join(DOCS_DIR, "positive_feedback.json")
            if os.path.exists(positive_file_path):
                try:
                    with open(positive_file_path, 'r', encoding='utf-8') as f:
                        positive_feedbacks = json.load(f)
                    
                    # qa_hash로 직접 검색하여 제거
                    positive_removed = False
                    positive_removed_feedback = None
                    for i, existing in enumerate(positive_feedbacks):
                        existing_qa_hash = existing.get("qa_hash")
                        if existing_qa_hash == qa_hash:
                            positive_removed_feedback = positive_feedbacks.pop(i)
                            positive_removed = True
                            logger.info(f"🗑️ 부정 피드백 저장: 긍정 피드백 파일에서 제거 - {question[:30]}...")
                            break
                    
                    # 제거된 항목이 있으면 파일 저장
                    if positive_removed:
                        with open(positive_file_path, 'w', encoding='utf-8') as f:
                            json.dump(positive_feedbacks, f, ensure_ascii=False, indent=2)
                        logger.info(f"✅ 긍정 피드백 파일에서 제거 완료: {positive_file_path}")
                        
                        # 벡터 DB에서도 제거
                        try:
                            feedback_vectordb = get_feedback_vectordb()
                            if feedback_vectordb:
                                collection = feedback_vectordb.get()
                                if collection and "ids" in collection and "metadatas" in collection:
                                    ids_to_remove = []
                                    documents = collection.get("documents", [])
                                    for i, metadata in enumerate(collection["metadatas"]):
                                        if isinstance(metadata, dict) and metadata.get("source") == "positive_feedback":
                                            metadata_question = documents[i] if i < len(documents) else ""
                                            metadata_answer = metadata.get("answer", "")
                                            metadata_qa_hash = hashlib.md5(f"{metadata_question}|||{metadata_answer}".encode('utf-8')).hexdigest()
                                            if metadata_qa_hash == qa_hash and i < len(collection["ids"]):
                                                ids_to_remove.append(collection["ids"][i])
                                    
                                    if ids_to_remove:
                                        feedback_vectordb._collection.delete(ids_to_remove)
                                        try:
                                            feedback_vectordb.persist()
                                        except Exception:
                                            pass
                                        logger.info(f"🗑️ 벡터 DB에서 피드백 제거: {len(ids_to_remove)}개")
                        except Exception as del_error:
                            logger.warning(f"⚠️ 벡터 DB에서 피드백 제거 중 오류 (무시하고 계속): {del_error}")
                except Exception as e:
                    logger.warning(f"⚠️ 긍정 피드백 파일 확인 중 오류 (무시하고 계속): {e}")
        
        # 반대 타입 파일에서 같은 질문-답변 세트 찾기 (피드백 타입 변경 처리)
        opposite_feedbacks = []
        opposite_index = None
        if os.path.exists(opposite_file):
            try:
                with open(opposite_file, 'r', encoding='utf-8') as f:
                    opposite_feedbacks = json.load(f)
                
                for i, existing in enumerate(opposite_feedbacks):
                    existing_qa_hash = existing.get("qa_hash")
                    if existing_qa_hash == qa_hash:
                        opposite_index = i
                        break
            except Exception as e:
                logger.warning(f"⚠️ 반대 타입 피드백 파일 읽기 오류: {e}")
        
        # 반대 타입에 같은 질문-답변 세트가 있으면 제거 (피드백 타입 변경)
        if opposite_index is not None:
            opposite_feedback = opposite_feedbacks[opposite_index]
            logger.info(f"🔄 피드백 타입 변경: {question[:30]}... ({'긍정' if feedback_type == 'positive' else '부정'}으로 변경)")
            
            # 반대 타입 파일에서 제거
            opposite_feedbacks.pop(opposite_index)
            try:
                # DOCS_DIR 디렉토리가 없으면 생성
                os.makedirs(DOCS_DIR, exist_ok=True)
                with open(opposite_file, 'w', encoding='utf-8') as f:
                    json.dump(opposite_feedbacks, f, ensure_ascii=False, indent=2)
                logger.info(f"✅ 반대 타입 피드백 파일 저장 완료: {opposite_file}")
            except Exception as save_error:
                logger.error(f"❌ 반대 타입 피드백 파일 저장 실패: {save_error}")
                raise
            
            # 기존 피드백 정보 보존 (카운트, 사용자 등)
            feedback_count = opposite_feedback.get("feedback_count", 1)
            feedback_users = opposite_feedback.get("feedback_users", [])
            
            # 새 타입으로 저장 (기존 정보 보존)
            feedback_data["qa_hash"] = qa_hash
            feedback_data["feedback_count"] = feedback_count
            feedback_data["first_feedback_time"] = opposite_feedback.get("first_feedback_time", opposite_feedback.get("timestamp"))
            feedback_data["last_feedback_time"] = feedback_data.get("timestamp", datetime.now().isoformat())
            feedback_data["feedback_users"] = feedback_users
            
            # 사용자 정보 추가
            user = feedback_data.get("user")
            if user and user not in feedback_users:
                feedback_data["feedback_users"].append(user)
            
            feedbacks.append(feedback_data)
            
            # 파일에 저장
            try:
                with open(feedback_file, 'w', encoding='utf-8') as f:
                    json.dump(feedbacks, f, ensure_ascii=False, indent=2)
                logger.info(f"✅ 피드백 파일 저장 완료: {feedback_file}")
            except Exception as save_error:
                logger.error(f"❌ 피드백 파일 저장 실패: {save_error}")
                raise  # 저장 실패 시 예외를 다시 발생시켜 상위에서 처리
            
            # 긍정 피드백으로 변경된 경우 벡터 DB 재인덱싱
            if feedback_type == "positive":
                index_feedback_data(feedback_file)
            # 부정 피드백으로 변경된 경우 벡터 DB에서 제거 (긍정 피드백만 인덱싱하므로)
            else:
                # 긍정 피드백 벡터 DB에서 해당 항목 제거
                try:
                    feedback_vectordb = get_feedback_vectordb()
                    if feedback_vectordb:
                        collection = feedback_vectordb.get()
                        if collection and "ids" in collection and "metadatas" in collection:
                            ids_to_remove = []
                            documents = collection.get("documents", [])
                            for i, metadata in enumerate(collection["metadatas"]):
                                if isinstance(metadata, dict) and metadata.get("source") == "positive_feedback":
                                    # 벡터 DB에는 질문이 documents[i]로, 답변이 metadata["answer"]로 저장됨
                                    metadata_question = documents[i] if i < len(documents) else ""
                                    metadata_answer = metadata.get("answer", "")
                                    metadata_qa_hash = hashlib.md5(f"{metadata_question}|||{metadata_answer}".encode('utf-8')).hexdigest()
                                    if metadata_qa_hash == qa_hash and i < len(collection["ids"]):
                                        ids_to_remove.append(collection["ids"][i])
                            
                            if ids_to_remove:
                                feedback_vectordb._collection.delete(ids_to_remove)
                                try:
                                    feedback_vectordb.persist()
                                except Exception:
                                    pass
                                logger.info(f"🗑️ 벡터 DB에서 피드백 제거: {len(ids_to_remove)}개")
                except Exception as del_error:
                    logger.warning(f"⚠️ 벡터 DB에서 피드백 제거 중 오류 (무시하고 계속): {del_error}")
            
            return {
                "saved": True,
                "is_new": False,
                "feedback_count": feedback_count,
                "type_changed": True
            }
        
        # 기존 피드백에서 동일한 질문-답변 세트 찾기
        existing_index = None
        same_question_index = None
        
        for i, existing in enumerate(feedbacks):
            existing_qa_hash = existing.get("qa_hash")
            if existing_qa_hash == qa_hash:
                existing_index = i
                break
            # 같은 질문이지만 답변이 다른 경우도 추적 (최신 답변으로 업데이트용)
            if existing.get("question") == question and same_question_index is None:
                same_question_index = i
        
        if existing_index is not None:
            # 동일한 질문-답변 세트가 이미 존재 → 피드백 카운트만 증가
            existing_feedback = feedbacks[existing_index]
            existing_feedback["feedback_count"] = existing_feedback.get("feedback_count", 1) + 1
            existing_feedback["last_feedback_time"] = feedback_data.get("timestamp", datetime.now().isoformat())
            existing_feedback["feedback_users"] = existing_feedback.get("feedback_users", [])
            
            # 사용자 정보 추가 (중복 제거)
            user = feedback_data.get("user")
            if user and user not in existing_feedback["feedback_users"]:
                existing_feedback["feedback_users"].append(user)
            
            logger.info(f"📊 피드백 카운트 증가: {question[:30]}... (총 {existing_feedback['feedback_count']}회)")
            
            # 파일에 저장
            try:
                with open(feedback_file, 'w', encoding='utf-8') as f:
                    json.dump(feedbacks, f, ensure_ascii=False, indent=2)
                logger.info(f"✅ 피드백 파일 저장 완료: {feedback_file}")
            except Exception as save_error:
                logger.error(f"❌ 피드백 파일 저장 실패: {save_error}")
                raise  # 저장 실패 시 예외를 다시 발생시켜 상위에서 처리
            
            # 긍정 피드백만 벡터 DB 재인덱싱 (카운트 증가해도 인덱싱은 필요 없을 수 있지만, 일관성 유지)
            if feedback_type == "positive":
                index_feedback_data(feedback_file)
            
            return {
                "saved": True,
                "is_new": False,
                "feedback_count": existing_feedback["feedback_count"]
            }
        
        elif same_question_index is not None:
            # 같은 질문이지만 답변이 다름 → 최신 답변으로 업데이트
            logger.info(f"🔄 같은 질문의 최신 답변으로 업데이트: {question[:30]}...")
            
            # 기존 피드백 정보 보존 (카운트, 사용자 등)
            old_feedback = feedbacks[same_question_index]
            feedback_count = old_feedback.get("feedback_count", 1)
            feedback_users = old_feedback.get("feedback_users", [])
            
            # 새 피드백으로 교체 (기존 정보 보존)
            feedback_data["qa_hash"] = qa_hash
            feedback_data["feedback_count"] = feedback_count
            feedback_data["first_feedback_time"] = old_feedback.get("first_feedback_time", old_feedback.get("timestamp"))
            feedback_data["last_feedback_time"] = feedback_data.get("timestamp", datetime.now().isoformat())
            feedback_data["feedback_users"] = feedback_users
            
            # 사용자 정보 추가
            user = feedback_data.get("user")
            if user and user not in feedback_users:
                feedback_data["feedback_users"].append(user)
            
            feedbacks[same_question_index] = feedback_data
            
            logger.info(f"💾 피드백 업데이트: {question[:30]}... (피드백 수: {feedback_count})")
        else:
            # 완전히 새로운 질문-답변 세트
            feedback_data["qa_hash"] = qa_hash
            feedback_data["feedback_count"] = 1
            feedback_data["first_feedback_time"] = feedback_data.get("timestamp", datetime.now().isoformat())
            feedback_data["last_feedback_time"] = feedback_data.get("timestamp", datetime.now().isoformat())
            feedback_data["feedback_users"] = []
            
            # 사용자 정보 추가
            user = feedback_data.get("user")
            if user:
                feedback_data["feedback_users"].append(user)
            
            feedbacks.append(feedback_data)
            logger.info(f"💾 새로운 피드백 저장: {question[:30]}... (총 {len(feedbacks)}개)")
        
        # 파일에 저장
        logger.info(f"💾 피드백 파일 저장 시도: {feedback_file} (데이터 {len(feedbacks)}개)")
        try:
            # 파일 저장 전 디렉토리 재확인
            feedback_dir = os.path.dirname(feedback_file) or DOCS_DIR
            os.makedirs(feedback_dir, exist_ok=True)
            
            # 파일 저장
            with open(feedback_file, 'w', encoding='utf-8') as f:
                json.dump(feedbacks, f, ensure_ascii=False, indent=2)
            
            # 파일이 제대로 생성되었는지 확인
            if not os.path.exists(feedback_file):
                raise FileNotFoundError(f"피드백 파일이 생성되지 않았습니다: {feedback_file}")
            
            # 파일 크기 확인
            file_size = os.path.getsize(feedback_file)
            logger.info(f"✅ 피드백 파일 저장 완료: {feedback_file} (크기: {file_size} bytes)")
                
        except Exception as save_error:
            logger.error(f"❌ 피드백 파일 저장 실패: {save_error}")
            logger.error(f"❌ 저장 경로: {feedback_file}")
            feedback_dir = os.path.dirname(feedback_file) or DOCS_DIR
            logger.error(f"❌ 디렉토리 존재: {os.path.exists(feedback_dir)}")
            logger.error(f"❌ 디렉토리 경로: {feedback_dir}")
            import traceback
            logger.error(f"❌ 상세 오류: {traceback.format_exc()}")
            raise  # 저장 실패 시 예외를 다시 발생시켜 상위에서 처리
        
        # 긍정 피드백만 벡터 DB 재인덱싱
        if feedback_type == "positive":
            index_feedback_data(feedback_file)
        
        return {
            "saved": True,
            "is_new": (same_question_index is None and existing_index is None),
            "feedback_count": feedback_data.get("feedback_count", 1)
        }
        
    except Exception as e:
        logger.error(f"❌ 피드백 저장 오류: {str(e)}")
        import traceback
        logger.error(f"❌ 상세 오류: {traceback.format_exc()}")
        return {"saved": False, "is_new": False, "feedback_count": 0}

def get_feedback_vectordb():
    """긍정 피드백 데이터 전용 벡터 DB"""
    try:
        embedding = OpenAIEmbeddings()
        feedback_db_path = os.path.join(DOCS_DIR, "feedback_chroma_db")
        vectordb = Chroma(persist_directory=feedback_db_path, embedding_function=embedding)
        
        # 자동 인덱싱 로직 제거 (순환 참조 방지)
        # 인덱싱은 save_feedback_to_file()에서만 수행
        
        return vectordb
    except Exception as e:
        logger.error(f"❌ 피드백 벡터 DB 초기화 실패: {e}")
        return None

def index_feedback_data(feedback_file):
    """긍정 피드백 데이터를 벡터 DB에 인덱싱"""
    try:
        with open(feedback_file, 'r', encoding='utf-8') as f:
            feedbacks = json.load(f)
        
        if not feedbacks:
            logger.info("📝 인덱싱할 피드백 데이터가 없습니다")
            return
        
        docs = []
        for feedback in feedbacks:
            doc = Document(
                page_content=feedback["question"],  # 질문을 벡터화
                metadata={
                    "answer": feedback["answer"],
                    "sources": json.dumps(feedback["sources"], ensure_ascii=False),
                    "timestamp": feedback["timestamp"],
                    "source": "positive_feedback"
                }
            )
            docs.append(doc)
        
        # 순환 참조 방지: get_feedback_vectordb() 대신 직접 벡터 DB 생성
        embedding = OpenAIEmbeddings()
        feedback_db_path = os.path.join(DOCS_DIR, "feedback_chroma_db")
        vectordb = Chroma(persist_directory=feedback_db_path, embedding_function=embedding)
        
        if docs:
            # 기존 피드백 데이터 제거 (전체 재인덱싱)
            try:
                collection = vectordb.get()
                if collection and "ids" in collection and collection["ids"]:
                    # positive_feedback 소스만 제거
                    ids_to_remove = []
                    if "metadatas" in collection:
                        for i, metadata in enumerate(collection["metadatas"]):
                            if isinstance(metadata, dict) and metadata.get("source") == "positive_feedback":
                                if i < len(collection["ids"]):
                                    ids_to_remove.append(collection["ids"][i])
                    
                    if ids_to_remove:
                        vectordb._collection.delete(ids_to_remove)
                        logger.info(f"🗑️ 기존 피드백 데이터 제거: {len(ids_to_remove)}개")
            except Exception as del_error:
                logger.warning(f"⚠️ 기존 피드백 데이터 삭제 중 오류 (무시하고 계속): {del_error}")
            
            # 새 데이터 추가
            vectordb.add_documents(docs)
            try:
                vectordb.persist()
            except Exception as persist_error:
                logger.warning(f"⚠️ persist() 중 오류 (무시하고 계속): {persist_error}")
            logger.info(f"✅ 피드백 데이터 인덱싱 완료: {len(docs)}개")
        
    except Exception as e:
        logger.error(f"❌ 피드백 데이터 인덱싱 오류: {str(e)}")
        import traceback
        logger.error(f"❌ 상세 오류: {traceback.format_exc()}")

def search_positive_feedback(question):
    """긍정 피드백 데이터에서 유사 질문 검색
    
    JSON 파일이 없으면 벡터 DB 검색을 하지 않고 None을 반환하여 메인 DB 검색으로 넘어감
    """
    try:
        # JSON 파일 존재 여부 확인 (파일 기반 검색 보장)
        positive_file = os.path.join(DOCS_DIR, "positive_feedback.json")
        if not os.path.exists(positive_file):
            logger.debug("📝 긍정 피드백 JSON 파일이 없어 벡터 DB 검색을 건너뜁니다 → 메인 DB 검색으로 진행")
            return None
        
        # JSON 파일이 비어있는지 확인 및 로드
        try:
            with open(positive_file, 'r', encoding='utf-8') as f:
                feedbacks = json.load(f)
            if not feedbacks or len(feedbacks) == 0:
                logger.debug("📝 긍정 피드백 JSON 파일이 비어있어 벡터 DB 검색을 건너뜁니다 → 메인 DB 검색으로 진행")
                return None
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"⚠️ 긍정 피드백 JSON 파일 읽기 오류: {e} → 메인 DB 검색으로 진행")
            return None
        
        # 1단계: JSON 파일 직접 검색 (벡터 DB 검색 전에 먼저 시도)
        # 핵심 키워드 추출 함수
        def extract_core_keywords(text, stop_words_set):
            """질문에서 핵심 키워드만 추출 (공백 제거 + stop_words 제거)"""
            if not text:
                return set()
            
            # 1. 소문자 변환
            text_lower = text.lower()
            # 2. 단어 분리 (원본에서)
            words = text_lower.split()
            # 3. stop_words 제거 후 핵심 단어 추출
            core_words = [w for w in words if len(w) > 1 and w not in stop_words_set]
            
            # 4. 핵심 키워드들만 합쳐서 공백 제거된 문자열 생성
            if core_words:
                core_no_space = "".join(core_words)
                if core_no_space and len(core_no_space) > 1:
                    core_words.append(core_no_space)
            
            return set(core_words)
        
        # stop_words 정의
        stop_words = {
            '공수', '의', '에', '을', '를', '이', '가', '은', '는', 
            '로', '으로', '와', '과', '도', '만', '까지', '부터', 
            '때문에', '위해', '대한', '관련', '기능', '개발', '작업',
            '알려줘', '알려주세요', '알려줍시다', '알려주시면', '알려',
            '분석해줘', '분석해주세요', '분석',
            '얼마야', '얼마예요', '얼마인가요', '얼마',
            '어떻게', '어떤', '어떠한',
            '돼', '되', '되어', '되는',
            '해줘', '해주세요', '해주시면', '해',
            '뭐야', '뭐예요', '무엇', '무엇인가',
            '?', '!', '.', ',', '는', '은', '이', '가'
        }
        
        # 일반적인 키워드 (매칭 시 가중치 감소)
        common_keywords = {'api', '시스템', '기능', '개발', '작업', '가이드'}
        
        # 질문에서 핵심 키워드 추출
        question_core = extract_core_keywords(question, stop_words)
        logger.info(f"🔍 JSON 파일 직접 검색 - 질문: '{question}', 핵심 키워드: {question_core}")
        
        # JSON 파일 내에서 직접 검색
        best_json_match = None
        best_json_score = 0.0
        
        for feedback in feedbacks:
            stored_question = feedback.get("question", "").lower()
            stored_core = extract_core_keywords(stored_question, stop_words)
            
            # 키워드 매칭 비율 계산
            if question_core and stored_core:
                # 1. 정확한 키워드 매칭
                matched_keywords = question_core.intersection(stored_core)
                
                # 2. 부분 문자열 매칭
                for q_keyword in question_core:
                    for s_keyword in stored_core:
                        if q_keyword in s_keyword or s_keyword in q_keyword:
                            matched_keywords.add(q_keyword)
                            matched_keywords.add(s_keyword)
                
                # 매칭 비율 계산
                if len(question_core) > 0:
                    matched_question_keywords = matched_keywords.intersection(question_core)
                    
                    # 일반 키워드만 매칭된 경우 가중치 감소
                    matched_common_only = matched_question_keywords.intersection(common_keywords)
                    matched_specific = matched_question_keywords - common_keywords
                    
                    if len(matched_specific) == 0 and len(matched_common_only) > 0:
                        keyword_match_ratio = (len(matched_question_keywords) / len(question_core)) * 0.5
                    else:
                        keyword_match_ratio = len(matched_question_keywords) / len(question_core)
                    
                    # 핵심 키워드가 모두 일치하면 100%로 처리
                    if question_core.issubset(matched_keywords):
                        keyword_match_ratio = 1.0
                else:
                    keyword_match_ratio = 0.0
            else:
                keyword_match_ratio = 0.0
            
            # JSON 파일 직접 검색: 기준2 - 거의 동일한 질문만 (키워드 100% 일치만 허용)
            # 띄어쓰기, 조사 차이만 있는 경우만 피드백 답변 사용
            is_match = False
            if keyword_match_ratio >= 1.0:
                # 핵심 키워드가 모두 일치하면 무조건 매칭 (기준2: 거의 동일한 질문)
                is_match = True
                logger.info(f"   ✅ JSON 파일에서 핵심 키워드 100% 일치 발견 (기준2): '{stored_question[:50]}...'")
            
            if is_match and keyword_match_ratio > best_json_score:
                best_json_score = keyword_match_ratio
                best_json_match = feedback
        
        # JSON 파일에서 매칭된 항목이 있으면 바로 반환
        if best_json_match:
            logger.info(f"✅ JSON 파일에서 직접 답변 발견 (키워드매칭={best_json_score:.3f})")
            return {
                "answer": best_json_match.get("answer", ""),
                "sources": best_json_match.get("sources", []),
                "question": best_json_match.get("question", ""),
                "is_from_feedback": True
            }
        
        # 2단계: JSON 파일에서 매칭되지 않으면 벡터 DB에서 검색 (기존 로직)
        logger.debug("📝 JSON 파일에서 직접 매칭되지 않음, 벡터 DB 검색으로 진행")
        
        # 벡터 DB에서 검색 (JSON 파일이 존재하고 비어있지 않을 때만)
        # 벡터 DB 초기화는 한 번만 수행하도록 최적화 (전역 변수 또는 캐싱 고려)
        try:
            # 벡터 DB 초기화 (매번 호출되지만 Chroma는 내부적으로 최적화됨)
            feedback_vectordb = get_feedback_vectordb()
            if not feedback_vectordb:
                logger.debug("📝 피드백 벡터 DB 초기화 실패 → 메인 DB 검색으로 진행")
                return None
            
            # 벡터 DB에 문서가 있는지 빠르게 확인
            try:
                doc_count = feedback_vectordb._collection.count()
                if doc_count == 0:
                    logger.debug("📝 피드백 벡터 DB에 문서가 없음 → 메인 DB 검색으로 진행")
                    return None
            except Exception as count_error:
                logger.debug(f"⚠️ 피드백 벡터 DB 문서 수 확인 실패: {count_error}, 검색 계속 진행")
            
            # 피드백 검색 최적화: similarity_search_with_score만 사용 (MMR 생략)
            # 피드백 데이터는 적으므로 빠른 검색이 중요
            # 띄어쓰기 차이를 고려하여 공백 제거 버전도 검색
            try:
                # 원본 질문으로 검색
                scored_docs = feedback_vectordb.similarity_search_with_score(question, k=5)
                
                # 공백 제거 버전으로도 검색 (띄어쓰기 차이 대응)
                question_no_space = question.replace(" ", "")
                if question_no_space != question:
                    scored_docs_no_space = feedback_vectordb.similarity_search_with_score(question_no_space, k=5)
                    # 두 결과를 합치고 중복 제거 (거리 기준으로 정렬)
                    all_docs = {}
                    for doc, score in scored_docs:
                        doc_key = doc.page_content
                        if doc_key not in all_docs or score < all_docs[doc_key][1]:
                            all_docs[doc_key] = (doc, score)
                    for doc, score in scored_docs_no_space:
                        doc_key = doc.page_content
                        if doc_key not in all_docs or score < all_docs[doc_key][1]:
                            all_docs[doc_key] = (doc, score)
                    # 거리 기준으로 정렬하여 상위 5개 선택
                    scored_docs = sorted(all_docs.values(), key=lambda x: x[1])[:5]
                
                if not scored_docs:
                    logger.debug("📝 피드백 벡터 DB에서 유사 질문을 찾지 못함 → 메인 DB 검색으로 진행")
                    return None
                
                docs_with_scores = [(doc, score) for doc, score in scored_docs]
            except (AttributeError, Exception) as e:
                # similarity_search_with_score가 없으면 MMR로 폴백
                logger.debug(f"⚠️ similarity_search_with_score 실패, MMR로 폴백: {e}")
                retriever = feedback_vectordb.as_retriever(
                    search_type="mmr",
                    search_kwargs={"k": 3, "fetch_k": 10}
                )
                docs = retriever.get_relevant_documents(question)
                if not docs:
                    logger.debug("📝 피드백 벡터 DB에서 유사 질문을 찾지 못함 → 메인 DB 검색으로 진행")
                    return None
                docs_with_scores = [(doc, 0.0) for doc in docs]
            
            if not docs_with_scores:
                logger.debug("📝 피드백 벡터 DB에서 유사 질문을 찾지 못함 → 메인 DB 검색으로 진행")
                return None
            
            # 질문에서 핵심 키워드 추출 (위에서 이미 추출했지만 벡터 DB 검색을 위해 재사용)
            logger.info(f"🔍 벡터 DB 검색 - 질문: '{question}', 핵심 키워드: {question_core}")
            
            # 유사도 점수와 키워드 매칭을 고려하여 최적의 결과 선택
            best_match = None
            best_score = 0.0
            
            # 기준2: 거의 동일한 질문만 피드백 답변 사용
            # 벡터 DB 검색에서는 거리 < 0.1 + 키워드 100% 일치만 허용
            # (기존 0.15보다 더 엄격하게 조정)
            
            # 유사도가 높지 않으면 키워드 매칭 수행
            for doc, score in docs_with_scores:
                # 유사도 점수 확인 (Chroma DB는 거리 기반이므로 낮을수록 유사함)
                # 거리를 유사도로 변환 (0~1 범위, 1에 가까울수록 유사)
                # 일반적으로 거리 1.0 이하를 유사하다고 봄
                similarity = 1.0 / (1.0 + score) if score > 0 else 1.0
                
                # 저장된 질문에서 핵심 키워드 추출
                stored_question = doc.page_content.lower()
                stored_core = extract_core_keywords(stored_question, stop_words)
                logger.debug(f"🔍 피드백 매칭 - 저장된 질문: '{stored_question}', 핵심 키워드: {stored_core}")
                
                # 키워드 매칭 비율 계산
                if question_core and stored_core:
                    # 1. 정확한 키워드 매칭
                    matched_keywords = question_core.intersection(stored_core)
                    
                    # 2. 부분 문자열 매칭 (공백 제거된 전체 문자열 포함)
                    # 저장된 질문의 핵심 키워드가 검색 질문에 포함되거나 그 반대인 경우
                    for q_keyword in question_core:
                        for s_keyword in stored_core:
                            # 부분 문자열 매칭 (양방향)
                            if q_keyword in s_keyword or s_keyword in q_keyword:
                                matched_keywords.add(q_keyword)
                                matched_keywords.add(s_keyword)
                    
                    # 매칭 비율 계산: 질문의 핵심 키워드 중 매칭된 비율 (더 엄격한 기준)
                    # 일반 키워드만 매칭된 경우 가중치 감소
                    if len(question_core) > 0:
                        # 질문의 핵심 키워드 중 매칭된 비율
                        matched_question_keywords = matched_keywords.intersection(question_core)
                        
                        # 일반 키워드만 매칭된 경우 가중치 감소
                        matched_common_only = matched_question_keywords.intersection(common_keywords)
                        matched_specific = matched_question_keywords - common_keywords
                        
                        # 일반 키워드만 있고 특정 키워드가 없으면 가중치 감소
                        if len(matched_specific) == 0 and len(matched_common_only) > 0:
                            # 일반 키워드만 매칭된 경우 가중치 50% 감소
                            keyword_match_ratio = (len(matched_question_keywords) / len(question_core)) * 0.5
                            logger.info(f"   ⚠️ 일반 키워드만 매칭됨 (가중치 50% 감소): {matched_common_only}")
                        else:
                            keyword_match_ratio = len(matched_question_keywords) / len(question_core)
                    else:
                        keyword_match_ratio = 0.0
                    
                    # 핵심 키워드가 모두 일치하면 키워드 매칭을 100%로 처리
                    # 단, 질문의 핵심 키워드가 모두 매칭되어야 함
                    if len(question_core) > 0 and question_core.issubset(matched_keywords):
                        keyword_match_ratio = 1.0
                else:
                    keyword_match_ratio = 0.0
                    matched_keywords = set()
                
                # 종합 점수 계산 (유사도 60% + 키워드 매칭 40%)
                # 키워드 매칭이 높으면 유사도가 낮아도 허용
                combined_score = (similarity * 0.6) + (keyword_match_ratio * 0.4)
                
                logger.info(f"🔍 피드백 매칭 점수: 유사도={similarity:.3f} (거리={score:.3f}), 키워드매칭={keyword_match_ratio:.3f}, 종합={combined_score:.3f}")
                logger.info(f"   질문: '{question}' (핵심키워드: {question_core}) vs 저장된: '{doc.page_content[:50]}...' (핵심키워드: {stored_core})")
                
                # 기준2: 거의 동일한 질문만 피드백 답변 사용
                # 벡터 DB 검색에서는 거리 < 0.1 + 키워드 100% 일치만 허용
                is_match = False
                if keyword_match_ratio >= 1.0 and score < 0.1:
                    # 핵심 키워드가 모두 일치하고 거리가 매우 가까울 때만 매칭 (기준2)
                    is_match = True
                    logger.info(f"   ✅ 기준2: 핵심 키워드 100% 일치 + 거리 {score:.3f} < 0.1로 매칭")
                
                if is_match:
                    if combined_score > best_score:
                        best_score = combined_score
                        best_match = (doc, similarity, keyword_match_ratio)
            
            if best_match:
                doc, similarity, keyword_match_ratio = best_match
                logger.info(f"✅ 피드백 벡터 DB에서 답변 발견 (유사도={similarity:.3f}, 키워드매칭={keyword_match_ratio:.3f})")
                return {
                    "answer": doc.metadata["answer"],
                    "sources": json.loads(doc.metadata["sources"]),
                    "question": doc.page_content,
                    "is_from_feedback": True
                }
            else:
                logger.debug(f"📝 피드백 벡터 DB에서 임계값을 만족하는 질문을 찾지 못함 (최고점수={best_score:.3f}) → 메인 DB 검색으로 진행")
                return None
            
        except Exception as vectordb_error:
            # 벡터 DB 오류가 발생해도 메인 DB 검색으로 넘어가도록 None 반환
            logger.warning(f"⚠️ 피드백 벡터 DB 검색 오류: {vectordb_error} → 메인 DB 검색으로 진행")
            return None
        
    except Exception as e:
        # 모든 오류를 잡아서 메인 DB 검색으로 넘어가도록 None 반환
        logger.warning(f"⚠️ 피드백 검색 중 예상치 못한 오류: {str(e)} → 메인 DB 검색으로 진행")
        return None

def index_json_data_incremental(jira_tickets: list, file_path: str = None):
    """특정 Jira 티켓들만 증분 색인 (추가/수정)"""
    try:
        if not file_path:
            file_path = os.path.join(DOCS_DIR, "effort_estimations.json")
        
        if not os.path.exists(file_path):
            logger.warning(f"⚠️ JSON 파일 없음: {file_path}")
            return False
        
        # 벡터 DB 생성
        embedding = OpenAIEmbeddings()
        vectordb = Chroma(persist_directory=CHROMA_DIR, embedding_function=embedding)
        
        # JSON 파일 읽기
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 대상 티켓만 필터링
        target_items = [item for item in data if item.get('jira_ticket') in jira_tickets]
        
        if not target_items:
            logger.info(f"📊 증분 색인: 대상 항목 없음")
            return True
        
        logger.info(f"📊 증분 색인: {len(target_items)}개 항목 처리 중...")
        
        # 기존 데이터 제거 (해당 티켓만) - 최적화: where 필터 사용
        try:
            # Chroma where 필터로 특정 티켓만 조회 (전체 DB 순회 없음)
            collection = vectordb.get(where={"jira_ticket": {"$in": jira_tickets}})
            docs_to_remove_ids = collection.get("ids", [])
            
            if docs_to_remove_ids:
                vectordb._collection.delete(docs_to_remove_ids)
                logger.info(f"   🗑️ 기존 데이터 제거: {len(docs_to_remove_ids)}개")
        except Exception as del_error:
            logger.warning(f"⚠️ 기존 데이터 제거 중 오류 (무시하고 계속): {del_error}")
        
        # 새 데이터 색인
        docs = []
        for item in target_items:
            # Epic 정보
            epic_info = ""
            if item.get('epic_key'):
                epic_info = f"\nEpic: {item.get('epic_key', '')}"
                if item.get('epic_name'):
                    epic_info += f" ({item.get('epic_name', '')})"
            
            # Story Points 표시 (원본 정보 포함)
            story_points_display = f"{item.get('story_points', '')} M/D"
            if item.get('story_points_unit') == 'M/M':
                story_points_display += f" (원본: {item.get('story_points_original', '')} M/M)"
            
            # 텍스트 생성
            text_content = f"""
Jira 티켓: {item.get('jira_ticket', '')}
제목: {item.get('title', '')}{epic_info}
Story Points: {story_points_display}
담당자: {item.get('team_member', '')}
산정 이유: {item.get('estimation_reason', '')}
설명: {item.get('description', '')}
댓글: {item.get('comments', '')}
비고: {item.get('notes', '')}
등록일: {item.get('created_date', '')}
"""
            
            doc = Document(
                page_content=text_content.strip(),
                metadata={
                    "source": "effort_estimations.json",
                    "jira_ticket": item.get('jira_ticket', ''),
                    "title": item.get('title', ''),
                    "story_points": item.get('story_points', ''),
                    "story_points_original": item.get('story_points_original', ''),
                    "story_points_unit": item.get('story_points_unit', 'M/D'),
                    "team_member": item.get('team_member', ''),
                    "major_category": item.get('major_category', ''),
                    "minor_category": item.get('minor_category', ''),
                    "sub_category": item.get('sub_category', ''),
                    "epic_key": item.get('epic_key', ''),
                    "epic_name": item.get('epic_name', ''),
                    "last_modified": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
                    "file_size": os.path.getsize(file_path)
                }
            )
            docs.append(doc)
        
        # 벡터 DB에 추가
        if docs:
            vectordb.add_documents(docs)
            try:
                vectordb.persist()
            except Exception:
                pass  # persist() 메서드가 없을 수 있음
            logger.info(f"   ✅ 증분 색인 완료: {len(docs)}개 추가")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 증분 색인 실패: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def index_json_data(file_path: str, force: bool = False):
    """JSON 파일을 벡터 DB에 인덱싱 (전체 재색인)"""
    try:
        # 직접 벡터 DB 생성 (get_vectordb() 호출하지 않음)
        embedding = OpenAIEmbeddings()
        vectordb = Chroma(persist_directory=CHROMA_DIR, embedding_function=embedding)
        
        # 기존 JSON 데이터 제거
        try:
            collection = vectordb.get()
            docs_to_remove = []
            if collection and "metadatas" in collection and "ids" in collection:
                for i, metadata in enumerate(collection["metadatas"]):
                    if isinstance(metadata, dict) and metadata.get("source") == "effort_estimations.json":
                        if i < len(collection["ids"]):
                            docs_to_remove.append(collection["ids"][i])
            
            if docs_to_remove:
                vectordb._collection.delete(docs_to_remove)
                logger.info(f"🗑️ Removed old JSON data: {len(docs_to_remove)} documents")
        except Exception as del_error:
            logger.warning(f"⚠️ 기존 데이터 삭제 중 오류 (무시하고 계속): {del_error}")
        
        # JSON 파일 읽기
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"📊 JSON 파일에서 {len(data)}개 항목을 읽었습니다")
        
        # JSON 데이터를 Document로 변환
        docs = []
        for item in data:
            # JSON 데이터를 검색 가능한 텍스트로 변환
            epic_info = ""
            if item.get('epic_key'):
                epic_info = f"\nEpic: {item.get('epic_key', '')}"
                if item.get('epic_name'):
                    epic_info += f" ({item.get('epic_name', '')})"
            
            # Story Points 표시 (원본 정보 포함)
            story_points_display = f"{item.get('story_points', '')} M/D"
            if item.get('story_points_unit') == 'M/M':
                story_points_display += f" (원본: {item.get('story_points_original', '')} M/M)"
            
            text_content = f"""
Jira 티켓: {item.get('jira_ticket', '')}
제목: {item.get('title', '')}{epic_info}
Story Points: {story_points_display}
담당자: {item.get('team_member', '')}
산정 이유: {item.get('estimation_reason', '')}
설명: {item.get('description', '')}
댓글: {item.get('comments', '')}
비고: {item.get('notes', '')}
등록일: {item.get('created_date', '')}
"""
            
            doc = Document(
                page_content=text_content.strip(),
                metadata={
                    "source": "effort_estimations.json",
                    "jira_ticket": item.get('jira_ticket', ''),
                    "title": item.get('title', ''),
                    "story_points": item.get('story_points', ''),
                    "story_points_original": item.get('story_points_original', ''),
                    "story_points_unit": item.get('story_points_unit', 'M/D'),
                    "team_member": item.get('team_member', ''),
                    "major_category": item.get('major_category', ''),
                    "minor_category": item.get('minor_category', ''),
                    "sub_category": item.get('sub_category', ''),
                    "epic_key": item.get('epic_key', ''),
                    "epic_name": item.get('epic_name', ''),
                    "last_modified": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
                    "file_size": os.path.getsize(file_path)
                }
            )
            docs.append(doc)
        
        logger.info(f"📊 총 {len(docs)}개 문서를 처리합니다")
        
        # 배치별로 문서 추가
        BATCH_SIZE = 10
        total_added = 0
        for i in range(0, len(docs), BATCH_SIZE):
            try:
                batch = docs[i:i + BATCH_SIZE]
                vectordb.add_documents(batch)
                # persist()는 선택적이므로 오류가 발생해도 계속 진행
                try:
                    vectordb.persist()
                except Exception as persist_error:
                    logger.warning(f"⚠️ persist() 중 오류 (무시하고 계속): {persist_error}")
                total_added += len(batch)
                logger.info(f"✅ Processed batch {i//BATCH_SIZE + 1} of {(len(docs)-1)//BATCH_SIZE + 1} (총 {total_added}개 문서 추가됨)")
            except Exception as batch_error:
                logger.error(f"❌ 배치 {i//BATCH_SIZE + 1} 처리 중 오류: {batch_error}")
                # 일부 배치 실패해도 계속 진행
                continue
        
        logger.info(f"✅ JSON 데이터 인덱싱 완료: {file_path} (총 {total_added}개 문서 저장됨)")
        return True
        
    except Exception as e:
        logger.error(f"❌ JSON 데이터 인덱싱 오류: {str(e)}")
        import traceback
        logger.error(f"❌ 상세 오류: {traceback.format_exc()}")
        return False