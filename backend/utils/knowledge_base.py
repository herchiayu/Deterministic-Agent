"""
知識庫向量化模組（多群組版）

每個群組對應 data/{group_name}/ 下的知識庫文件，
各自擁有獨立的 ChromaDB collection。

使用方式：
  from utils.knowledge_base import kb

  kb.build_all_indexes()                                   # 啟動時建立所有群組索引
  kb.build_all_indexes(force_rebuild=True)                 # 重建所有索引
  results = kb.search("爬電距離", groups=['RD_ME'])         # 單群組檢索
  results = kb.search("爬電距離", groups=['Developer', 'RD_ME'])  # 多群組檢索
"""

import re
from pathlib import Path
from google import genai
from config import config as cfg
import chromadb


class KnowledgeBase:
    """知識庫管理器：切段、向量化、多群組檢索"""

    def __init__(self):
        self._gemini_client = None
        self._chroma_client = None

    # ─── 延遲初始化 ───

    @property
    def gemini_client(self):
        if self._gemini_client is None:
            self._gemini_client = genai.Client(api_key=cfg.GEMINI_API_KEY)
        return self._gemini_client

    @property
    def chroma_client(self):
        if self._chroma_client is None:
            cfg.CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)
            self._chroma_client = chromadb.PersistentClient(
                path=str(cfg.CHROMA_DB_DIR)
            )
        return self._chroma_client

    def _get_collection(self, group: str):
        """取得指定群組的 ChromaDB collection"""
        return self.chroma_client.get_or_create_collection(
            name=group,
            metadata={'hnsw:space': 'cosine'},
        )

    # ─── 文件切段 ───

    def chunk_document(self, text: str, filename: str, uploader: str = 'system') -> list[dict]:
        """
        將文件依 Markdown 標題切段。
        回傳格式：[{'id': ..., 'text': ..., 'source': ..., 'uploader': ...}, ...]
        """
        chunks = []
        sections = re.split(r'(?=^#{1,3}\s)', text, flags=re.MULTILINE)

        for i, section in enumerate(sections):
            section = section.strip()
            if not section:
                continue

            if len(section) > cfg.CHUNK_SIZE:
                sub_chunks = self._split_by_size(section)
                for j, sub in enumerate(sub_chunks):
                    chunks.append({
                        'id': f'{uploader}/{filename}::chunk_{i}_{j}',
                        'text': sub,
                        'source': filename,
                        'uploader': uploader,
                    })
            else:
                chunks.append({
                    'id': f'{uploader}/{filename}::chunk_{i}',
                    'text': section,
                    'source': filename,
                    'uploader': uploader,
                })

        return chunks

    def _split_by_size(self, text: str) -> list[str]:
        """依 CHUNK_SIZE 和 CHUNK_OVERLAP 將長文切成小段"""
        chunks = []
        start = 0
        while start < len(text):
            end = start + cfg.CHUNK_SIZE
            chunk = text[start:end]

            if end < len(text):
                last_break = max(
                    chunk.rfind('\n\n'),
                    chunk.rfind('。'),
                    chunk.rfind('\n'),
                )
                if last_break > cfg.CHUNK_SIZE // 2:
                    end = start + last_break + 1
                    chunk = text[start:end]

            chunks.append(chunk.strip())
            start = end - cfg.CHUNK_OVERLAP

        return [c for c in chunks if c]

    # ─── 向量化 ───

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        """呼叫 Gemini Embedding API 將文字轉為向量"""
        all_embeddings = []
        batch_size = 100

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            result = self.gemini_client.models.embed_content(
                model=cfg.EMBEDDING_MODEL,
                contents=batch,
            )
            all_embeddings.extend([e.values for e in result.embeddings])

        return all_embeddings

    # ─── 索引建立 ───

    def _discover_groups(self) -> list[str]:
        """掃描 data/ 下的子目錄，每個子目錄視為一個群組"""
        groups = []
        for d in sorted(cfg.KNOWLEDGE_BASE_DIR.iterdir()):
            if d.is_dir() and d.name != 'chroma_db':
                groups.append(d.name)
        return groups

    def build_group_index(self, group: str, force_rebuild: bool = False):
        """建立單一群組的向量索引"""
        group_dir = cfg.KNOWLEDGE_BASE_DIR / group

        if force_rebuild:
            try:
                self.chroma_client.delete_collection(group)
            except Exception:
                pass

        collection = self._get_collection(group)

        if collection.count() > 0 and not force_rebuild:
            print(f'[知識庫] {group} 索引已存在（{collection.count()} 段），跳過')
            return

        # 讀取該群組目錄下的所有 {username}/*.md|*.txt
        all_chunks = []
        if group_dir.exists():
            for user_dir in sorted(group_dir.iterdir()):
                if not user_dir.is_dir():
                    continue
                uploader = user_dir.name
                for ext in ('*.md', '*.txt'):
                    for f in sorted(user_dir.glob(ext)):
                        text = f.read_text(encoding='utf-8')
                        chunks = self.chunk_document(text, f.name, uploader)
                        all_chunks.extend(chunks)

        if not all_chunks:
            print(f'[知識庫] {group} 沒有知識庫文件')
            return

        print(f'[知識庫] {group} 共 {len(all_chunks)} 段，開始向量化...')

        texts = [c['text'] for c in all_chunks]
        embeddings = self._embed_texts(texts)

        collection.add(
            ids=[c['id'] for c in all_chunks],
            documents=texts,
            embeddings=embeddings,
            metadatas=[{'source': c['source'], 'uploader': c['uploader']} for c in all_chunks],
        )

        print(f'[知識庫] {group} 索引建立完成，共 {collection.count()} 段')

    def build_all_indexes(self, force_rebuild: bool = False):
        """掃描所有群組目錄，建立全部索引"""
        groups = self._discover_groups()
        if not groups:
            print('[知識庫] 沒有找到任何群組目錄')
            return

        print(f'[知識庫] 發現群組：{groups}')
        for group in groups:
            self.build_group_index(group, force_rebuild=force_rebuild)

    # ─── 檢索 ───

    def search(self, query: str, groups: list[str] = None, top_k: int = None) -> str:
        """
        同時搜尋多個群組的 collection，
        依相似度合併排序後回傳前 top_k 段。
        """
        if top_k is None:
            top_k = cfg.TOP_K_RESULTS

        if not groups:
            groups = [cfg.DEFAULT_GROUP]

        query_embedding = self._embed_texts([query])[0]

        # 從每個群組的 collection 搜尋
        all_results = []  # [(distance, document, source, uploader)]
        for group in groups:
            collection = self._get_collection(group)
            if collection.count() == 0:
                continue

            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, collection.count()),
                include=['documents', 'distances', 'metadatas'],
            )

            if results['documents'] and results['distances']:
                for doc, dist, meta in zip(
                    results['documents'][0],
                    results['distances'][0],
                    results['metadatas'][0],
                ):
                    all_results.append((
                        dist, doc,
                        meta.get('source', ''),
                        meta.get('uploader', ''),
                    ))

        if not all_results:
            return ''

        # 依距離排序（cosine distance 越小越相似）
        all_results.sort(key=lambda x: x[0])

        # 取前 top_k 段，附帶來源與上傳者標示
        segments = []
        for _, doc, source, uploader in all_results[:top_k]:
            header = f'[來源: {source} | 上傳者: {uploader}]'
            segments.append(f'{header}\n{doc}')

        return '\n\n---\n\n'.join(segments)


# 全域單例
kb = KnowledgeBase()
