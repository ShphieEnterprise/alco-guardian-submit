# エージェントアーキテクチャ設計方針

## 🎯 基本方針

このプロジェクトでは、Google Agent Development Kit (ADK) と Agent-to-Agent (A2A) プロトコルを積極的に活用し、真のマルチエージェントシステムを構築します。

### 重要な設計原則

1. **エージェントファースト思考**
   - すべての機能をエージェントとして実装
   - 単なる関数やAPIではなく、自律的な判断能力を持つエージェントとして設計

2. **A2A通信の活用**
   - エージェント間の通信はA2Aプロトコルに準拠
   - 直接的な関数呼び出しではなく、メッセージパッシングで協調

3. **Google ADKの最大活用**
   - ADKが提供するエージェント開発機能をフル活用
   - Gemini APIの高度な機能（Function Calling、Grounding等）を組み込み

## 📐 アーキテクチャ構成

### エージェント定義

```yaml
# agent_definitions.yaml
agents:
  bartender:
    name: "Bartender Agent"
    model: "gemini-2.0-flash"
    capabilities:
      - conversation
      - drink_recommendation
      - context_awareness
    a2a_messages:
      publishes:
        - drink.suggested
        - mood.detected
      subscribes:
        - guardian.veto
        - health.warning
        
  guardian:
    name: "Guardian Agent"
    model: "gemini-2.0-flash"
    capabilities:
      - pace_monitoring
      - alcohol_calculation
      - risk_assessment
    a2a_messages:
      publishes:
        - guardian.veto
        - pace.alert
        - session.stats
      subscribes:
        - drink.added
        - session.started
```

### A2Aメッセージフォーマット

```json
{
  "messageId": "msg_123",
  "from": "guardian",
  "to": "bartender",
  "type": "guardian.veto",
  "timestamp": "2025-06-28T10:30:00Z",
  "payload": {
    "reason": "飲酒ペースが速すぎます",
    "severity": "warning",
    "suggestions": ["水分補給", "休憩"]
  }
}
```

## 🛠 実装ガイドライン

### 1. エージェントクラスの基本構造

```python
from google.cloud import aiplatform
from typing import Dict, Any
import asyncio

class BaseAgent:
    """ADKベースのエージェント基底クラス"""
    
    def __init__(self, agent_id: str, model_name: str = "gemini-2.0-flash"):
        self.agent_id = agent_id
        self.model = aiplatform.GenerativeModel(model_name)
        self.message_queue = asyncio.Queue()
        self.subscriptions = {}
        
    async def process_message(self, message: Dict[str, Any]):
        """A2Aメッセージを処理"""
        message_type = message.get("type")
        if message_type in self.subscriptions:
            handler = self.subscriptions[message_type]
            return await handler(message)
            
    async def publish_message(self, to: str, message_type: str, payload: Dict):
        """A2Aメッセージを発行"""
        # Message broker (Pub/Sub or Firestore) に発行
        pass
        
    def subscribe(self, message_type: str, handler):
        """メッセージタイプにハンドラを登録"""
        self.subscriptions[message_type] = handler
```

### 2. Bartenderエージェントの実装例

```python
class BartenderAgent(BaseAgent):
    """ADKベースのBartenderエージェント"""
    
    def __init__(self):
        super().__init__("bartender", "gemini-2.0-flash")
        
        # Guardian vetoメッセージを購読
        self.subscribe("guardian.veto", self.handle_guardian_veto)
        
    async def chat(self, user_message: str, context: Dict) -> str:
        """ユーザーとの会話を処理"""
        
        # コンテキストを含むプロンプトを構築
        prompt = self._build_prompt(user_message, context)
        
        # Geminiで応答生成（Function Callingも活用）
        response = await self.model.generate_content_async(
            prompt,
            generation_config={
                "temperature": 0.7,
                "candidate_count": 1,
            }
        )
        
        # 飲み物の提案を検出したらA2Aメッセージ発行
        if self._detect_drink_suggestion(response.text):
            await self.publish_message(
                to="guardian",
                message_type="drink.suggested",
                payload={
                    "drink_type": "beer",
                    "context": user_message
                }
            )
        
        return response.text
        
    async def handle_guardian_veto(self, message: Dict):
        """Guardianからの拒否権を処理"""
        # 内部状態を更新して、次の応答に反映
        self.guardian_warning = message["payload"]
```

### 3. エージェント間通信の実装

```python
# A2A Message Broker (Cloud Pub/Sub or Firestore-based)
class A2AMessageBroker:
    """エージェント間メッセージングを管理"""
    
    def __init__(self):
        self.agents = {}
        self.topic_subscriptions = defaultdict(list)
        
    def register_agent(self, agent: BaseAgent):
        """エージェントを登録"""
        self.agents[agent.agent_id] = agent
        
    async def publish(self, message: Dict[str, Any]):
        """メッセージを配信"""
        message_type = message["type"]
        for agent in self.topic_subscriptions[message_type]:
            await agent.process_message(message)
```

## 🔧 開発時の確認事項

### Gemini CLIを使った調査

不明な点がある場合は、Gemini CLIを活用して調査：

```bash
# ADKの最新機能を確認
gemini query "Google Agent Development Kit latest features"

# A2Aプロトコルのベストプラクティス
gemini query "Agent-to-Agent protocol best practices"

# Function Callingの実装例
gemini query "Gemini Function Calling implementation examples"
```

## 📋 実装チェックリスト

- [ ] 各エージェントがBaseAgentを継承している
- [ ] A2Aメッセージフォーマットに準拠している
- [ ] エージェント間の直接的な関数呼び出しを避けている
- [ ] Gemini APIの高度な機能を活用している
- [ ] 非同期処理でスケーラビリティを確保している
- [ ] エージェントの自律性が保たれている

## 🚀 次のステップ

1. 既存のコードをエージェントベースにリファクタリング
2. Cloud Pub/SubまたはFirestoreベースのA2Aブローカー実装
3. エージェントのデプロイとオーケストレーション設定
4. エージェント間の協調動作テスト

## 参考資料

- [Google Agent Development Kit Documentation](https://cloud.google.com/agent-builder/docs)
- [Gemini API Documentation](https://ai.google.dev/gemini-api/docs)
- [A2A Protocol Specification](https://cloud.google.com/agent-builder/docs/a2a-protocol)