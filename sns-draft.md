# SNS Post Drafts

---

## LinkedIn (English)

---

Built a small PoC this week to compare three AI agent control models on the same task:

- **Single loop** — one agent, one growing context window
- **Orchestrator + workers** — manager delegates via `Agent.as_tool()`, workers return summaries only
- **Handoff** — triage transfers ownership to a specialist, filtering history at the boundary

Key takeaway: multi-agent architecture mainly changes *who decides the next action* and *which history they can see*. That's it. Everything else follows from that.

Honest caveat: the preset tasks are simple one-liners, so the orchestrator looks like overkill here — because for these inputs, it is. The README has instructions for swapping in longer multi-step tasks where the isolation actually matters.

Includes a local web UI that draws each flow as a swimlane timeline with token costs per step.

---

On a related note: I'm planning to join an **AI Agent hackathon next month**. This PoC was part of getting my hands dirty before the event. If you're also participating or just interested in agent system design, I'd love to connect.

Repo: [agent-architectures on GitHub] <!-- add link when public -->

#AIAgents #OpenAI #AgentSDK #MultiAgent #LLM #Python #SoftwareEngineering #Hackathon

---

---

## Viva Engage（社内SNS・日本語）

---

以前の投稿でオーケストレーター＆ワーカーの設計について書きましたが、今回はそれを**実際に動くコード**に落とし込み、PoC を作りました。

**Agent Architectures PoC**

同じタスクを3つの制御モデルで実行し、何が変わるかを並べて確認できる実験台です。

| フロー | 制御の置き場 | コンテキストの扱い |
|---|---|---|
| Single loop | 1エージェントが全部やる | ウィンドウに生の結果が積み上がる |
| Orchestrator | マネージャーが制御を保持し続ける | ワーカーは要約だけを返す |
| Handoff | トリアージが責任ごと渡す | 受け手がフィルタ済みの会話を引き継ぐ |

以前の投稿でお伝えした「**オーケストレーターはコントロールを手放さない**」という原則が、`Agent.as_tool()` という SDK のプリミティブに直接対応しているのが、実際に動かしてみると一目瞭然でした。ハンドオフとは何が違うか、コンテキスト隔離のコストはどこに出るか、といった点も含めて体感できました。

ローカル Web UI もつけていて、各フローをスイムレーンのタイムラインで可視化できます。トークン消費やコストも並べて見れるので、「設計の違いが実行コストにどう出るか」も分かります。

**一点、正直に言っておくと：** 今回のプリセットタスクは意図的に短い一問一答形式にしています。制御構造の違いを見るには十分ですが、**オーケストレーターの本領を発揮させるには不十分**です。ワーカーへの並列委譲やサマリー圧縮が効いてくるのは、タスクが長くなってシングルループのコンテキストが膨れ上がってから。マルチステップかつ複数ソースを要する質問に差し替えると、様相はかなり変わります。README にそのやり方を書いておいたので、興味があれば試してみてください。

学習アーティファクトとして結論づけた PoC ですが、ここで掴んだ制御／コンテキストのトレードオフは実機能設計でも直接使えると思っています。興味のある方はぜひ見てください。

---
