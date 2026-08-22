# AGENTS.md — science-researcher 固有指示

ユーザー共通指示 (`~/.pi/agent/AGENTS.md`) より優先される、このリポジトリ固有の方針。

## 問題選択ポリシー: formal 中心

研究ストアの未解決問題カードには `metadata.agent_testability` タグが付いている。
エージェントの検証労力はこの順で配分する:

1. **`formal`** — 主体。数学的証明・計算的反証・ベンチマーク実験だけで
   進捗が完結する問題 (例: Frankl, planted clique, 編集距離壁,
   ループ不変式推論, オークション設計)。
2. **`simulable`** — 補助。縮約シミュレーション (シェルモデル, CA,
   population genetics モデル等) で仮説のメカニズム検証まで可能な問題。
   「解決」には実験が要ることを RESULTS.md に明記すること。
3. **`empirical` = not planned** — エージェント作業の対象にしない。
   実験・観測が解決の主体である問題 (触媒, 電池, 圃場, 臨床, 地震観測等)。
   ストアには `planned: false` 付きで登録し、組み合わせ仮説の生成先と
   アナロジー源としてのみ使う。ミラー issue は `not-planned` ラベル付きで
   closed (not planned)。

新規問題カードを登録するときは必ずこのタグを付け、既存カードを
empirical → simulable/formal へ引き上げるときは根拠 (検証可能な
サロゲートの特定) を metadata に残す。

## 数学問題への取り組み方: セマンティックな論理的解決

formal 問題でも、総当たり的な計算による境界延長を「検証」として納品しては
いけない。求められるのは:

- 補題連鎖の構築と、それがどこで破綻するかの正確な特定
- 構造的な証明試み (算術構造、単調性、対称性、帰納の破綻点など)
- 計算は状態絞り込み・小さい場合の境界確認という補助に限定。
  計算結果自体が主成果 (search-bound extension) になることはない。

成果物は `THEORY.md` として定義 → 試みた補題 → 破綻点 → 必要な次の手
という構成で書く。

## THEORY 判定語彙 (formal 攻略の verdict)

`THEORY.md` の verdict と `metadata.attack_notes.verdict` に使う語彙は
**`docs/theory-verdicts.md` で定義された体系のみ**。下の「検証の梯子」の
SUPPORT / AGAINST / INCONCLUSIVE とは別系統で、混ぜてはいけない。

判定は必ず 2つの門 → ラダーの順で行う:

1. **Gate A (連鎖健全性)** — verdict が依拠する補題すべてに文書内の証明が
   あるか。数値確認は補題の代わりにならない。特に「新補題 NL は問題 P と
   同値な強さ」と書くときは `P ⇒ NL` (exhaustion lemma) を別途証明する。
   NL が帰着の生んだ族の真部分族に対する主張なら、証明なしに同値とは
   言えない。抜けがあれば `CHAIN-GAP`。
2. **Gate B (先行研究照合)** — 使った帰着・パラメトリゼーション・分類・
   主張した obstruction について、解決可能な引用を挙げた節が文書にあるか。
   「記憶に基づく・未検証」は引用ではない。無ければ `PRIOR-ART-PENDING`。
3. 両方を通ったときだけラダーのラベル
   (`ROUTE-DEAD` / `ROUTE-KNOWN` / `OBSTRUCTION-IDENTIFIED` / `ROUTE-LIVE`)
   を付ける。`ROUTE-LIVE` は Gate B が必須であって任意ではない。

verdict の格下げは通常の運用であって失敗ではない。旧ラベルは
`attack_notes.previous` に理由付きで積み、`THEORY.md` の該当箇所は削除せず
その場で訂正する。

## 検証の梯子 (仮説の進め方)

1. 組み合わせ仮説には必ず `cheap_falsification` (安い反証テスト) を
   pre-register してから実験する。基準は結果を見る前に書く。
2. verdict (SUPPORT / AGAINST / INCONCLUSIVE) は
   - 実験コード + RESULTS.md を worktree ブランチで commit → PR → main
   - claim の `metadata.assessment` / `metadata.verification` を更新して
     冪等 re-import (`make sync-issues` で issue ミラーも更新)
3. SUPPORT は「次の反証ステージに上げる」ことしか意味しない。
   問題の解決とは別物。stage を上げるときは基準も一段厳しく再登録する。

## データフロー: DB 主 / Git アーカイブ

- claims/evidence/vectors の一次は Neon Postgres (`--store postgres`)。
  登録・更新は CLI (`add-claim`, `import-research`) 経由で行う。
- `research/*.json` バンドルは冪等 import のソースでありバックアップ。
  大きな編集はバンドル経由でもよいが、日々の運用は DB 主。
- `make backup` で全ストアを gz+base64 で単一 issue に退避、
  `make restore ISSUE=N` で復元。
- GitHub issue は claim のミラー (1 claim = 1 issue)。未解決問題が親、
  その問題を狙う仮説・先例カードが sub-issue。`make sync-issues` で同期。

## サブプロセス検証の作法

- 検証実験は共有ツリーを触らず `git worktree add` で切り、そこでヘッドレス
  `pi -p` を走らせる。
- プロンプトには (a) 対象 claim の external_id, (b) pre-register した判定基準,
  (c) 成果物の配置 (`experiments/<name>/`), (d) commit 前の author 上書きと
  Co-Authored-By ルールを含めること。
- ランタイム上限 (目安 10〜45 分 compute) をプロンプトに明記する。
