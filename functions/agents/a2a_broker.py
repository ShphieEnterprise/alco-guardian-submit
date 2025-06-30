"""
A2A (Agent-to-Agent) Message Broker
エージェント間の通信を管理
"""
import logging
import asyncio
from typing import Dict, Any, List, Callable
from datetime import datetime
from collections import defaultdict
import json

from google.cloud import firestore
from google.adk.messages import Message


class A2ABroker:
    """
    エージェント間メッセージングブローカー
    Firestoreを使用してメッセージを永続化し、リアルタイム配信を行う
    """
    
    def __init__(self, project_id: str = None):
        self.db = firestore.Client(project=project_id)
        self.agents = {}  # agent_id -> agent instance
        self.subscriptions = defaultdict(list)  # message_type -> [agent_ids]
        self.message_handlers = {}  # agent_id -> handler function
        
        # メッセージ履歴コレクション
        self.messages_collection = self.db.collection('a2a_messages')
        
        # リアルタイム配信用のキュー
        self.message_queues = defaultdict(asyncio.Queue)  # agent_id -> Queue
        
    def register_agent(self, agent_id: str, agent_instance: Any, 
                      subscriptions: List[str], handler: Callable):
        """
        エージェントを登録
        
        Args:
            agent_id: エージェントの識別子
            agent_instance: エージェントのインスタンス
            subscriptions: 購読するメッセージタイプのリスト
            handler: メッセージハンドラ関数
        """
        self.agents[agent_id] = agent_instance
        self.message_handlers[agent_id] = handler
        
        # 購読設定
        for message_type in subscriptions:
            self.subscriptions[message_type].append(agent_id)
            
        # メッセージキューを作成
        self.message_queues[agent_id] = asyncio.Queue()
        
        logging.info(f"Agent registered: {agent_id}, subscriptions: {subscriptions}")
    
    async def publish(self, message: Message):
        """
        A2Aメッセージを発行
        
        Args:
            message: 発行するメッセージ
        """
        # メッセージにメタデータを追加
        message_dict = {
            "message_id": message.message_id or f"msg_{datetime.now().timestamp()}",
            "type": message.type,
            "from_agent": message.from_agent,
            "to_agent": message.to_agent,
            "payload": message.payload,
            "timestamp": message.timestamp or datetime.now().isoformat(),
            "processed": False
        }
        
        # Firestoreに保存
        doc_ref = self.messages_collection.add(message_dict)
        message_dict["firestore_id"] = doc_ref[1].id
        
        logging.info(f"A2A Message published: {message.type} from {message.from_agent} to {message.to_agent}")
        
        # 配信先を決定
        recipients = []
        if message.to_agent == "all":
            # 全エージェントに配信（送信者を除く）
            recipients = [aid for aid in self.agents.keys() if aid != message.from_agent]
        elif message.to_agent in self.agents:
            # 特定のエージェントに配信
            recipients = [message.to_agent]
        else:
            # メッセージタイプの購読者に配信
            recipients = self.subscriptions.get(message.type, [])
        
        # 各受信者のキューにメッセージを追加
        for agent_id in recipients:
            if agent_id in self.message_queues:
                await self.message_queues[agent_id].put(message_dict)
        
        return message_dict
    
    async def start_message_processor(self, agent_id: str):
        """
        エージェントのメッセージ処理ループを開始
        
        Args:
            agent_id: 処理を開始するエージェントID
        """
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not registered")
            
        queue = self.message_queues[agent_id]
        handler = self.message_handlers[agent_id]
        
        logging.info(f"Starting message processor for agent: {agent_id}")
        
        while True:
            try:
                # キューからメッセージを取得
                message_dict = await queue.get()
                
                # メッセージオブジェクトに変換
                message = Message(
                    type=message_dict["type"],
                    from_agent=message_dict["from_agent"],
                    to_agent=message_dict["to_agent"],
                    payload=message_dict["payload"],
                    timestamp=message_dict["timestamp"],
                    message_id=message_dict["message_id"]
                )
                
                # ハンドラを呼び出し
                logging.info(f"Agent {agent_id} processing message: {message.type}")
                await handler(message)
                
                # 処理済みフラグを更新
                if "firestore_id" in message_dict:
                    self.messages_collection.document(message_dict["firestore_id"]).update({
                        "processed": True,
                        "processed_by": agent_id,
                        "processed_at": datetime.now().isoformat()
                    })
                    
            except Exception as e:
                logging.error(f"Error processing message for agent {agent_id}: {e}")
                await asyncio.sleep(1)  # エラー時は少し待機
    
    async def get_message_history(self, agent_id: str = None, 
                                message_type: str = None,
                                limit: int = 100) -> List[Dict]:
        """
        メッセージ履歴を取得
        
        Args:
            agent_id: フィルタするエージェントID
            message_type: フィルタするメッセージタイプ
            limit: 取得する最大件数
            
        Returns:
            メッセージのリスト
        """
        query = self.messages_collection.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit)
        
        if agent_id:
            query = query.where("from_agent", "==", agent_id)
        if message_type:
            query = query.where("type", "==", message_type)
            
        messages = []
        for doc in query.get():
            message_data = doc.to_dict()
            message_data["id"] = doc.id
            messages.append(message_data)
            
        return messages
    
    def get_agent_stats(self) -> Dict[str, Any]:
        """
        エージェントの統計情報を取得
        
        Returns:
            統計情報の辞書
        """
        stats = {
            "registered_agents": list(self.agents.keys()),
            "subscriptions": dict(self.subscriptions),
            "queue_sizes": {
                agent_id: queue.qsize() 
                for agent_id, queue in self.message_queues.items()
            },
            "timestamp": datetime.now().isoformat()
        }
        return stats


# シングルトンインスタンス
_broker_instance = None


def get_broker() -> A2ABroker:
    """A2Aブローカーのシングルトンインスタンスを取得"""
    global _broker_instance
    if _broker_instance is None:
        _broker_instance = A2ABroker()
    return _broker_instance


async def setup_agents(broker: A2ABroker):
    """
    全エージェントをブローカーに登録
    """
    from agents.bartender_adk import create_bartender_service
    from agents.guardian_adk import create_guardian_service
    
    # Bartenderエージェント
    bartender = create_bartender_service()
    broker.register_agent(
        agent_id="bartender",
        agent_instance=bartender,
        subscriptions=["guardian.veto", "health.warning", "mood.update"],
        handler=bartender.handle_a2a_message
    )
    
    # Guardianエージェント
    guardian = create_guardian_service()
    broker.register_agent(
        agent_id="guardian",
        agent_instance=guardian,
        subscriptions=["drink.added", "drink.suggested", "session.started", "bartender.chat"],
        handler=guardian.handle_a2a_message
    )
    
    # 各エージェントのメッセージプロセッサを起動
    asyncio.create_task(broker.start_message_processor("bartender"))
    asyncio.create_task(broker.start_message_processor("guardian"))
    
    logging.info("All agents registered and message processors started")


# 使用例
async def example_usage():
    """A2Aブローカーの使用例"""
    broker = get_broker()
    
    # エージェントをセットアップ
    await setup_agents(broker)
    
    # メッセージを発行
    test_message = Message(
        type="session.started",
        from_agent="system",
        to_agent="all",
        payload={
            "user_id": "test_user",
            "session_id": "test_session",
            "timestamp": datetime.now().isoformat()
        }
    )
    
    await broker.publish(test_message)
    
    # 統計情報を表示
    stats = broker.get_agent_stats()
    print(f"Broker stats: {json.dumps(stats, indent=2)}")