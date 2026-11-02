# presentation

完成したプレゼンテーションスライドを、ぺんた（@plageoj）のプレゼンテーションスタイルに照らして評価し、修正提案と自動修正を行う Claude Code の skill です。

「話しながら見せるスライド」として機能するかを、次の三原則で評価します。

1. メッセージが伝わる
2. スライドを見れば話をたどれる
3. スライド自体がタイマーになる（1 枚 20〜30 秒）

スタイルの評価とは別に、未完成の痕跡・誤字・発表者ノートとのずれ・権利のリスクなど、内容のレビューも行います。

## 対応する形式

| 形式 | 評価 | 自動修正 |
|:--|:--|:--|
| PDF | ○ | なし（修正提案のみ） |
| Marp（Markdown） | ○ | git 管理下なら直接、そうでなければ `<名前>.revised.md` に出力 |
| pptx | ○（LibreOffice で変換） | なし（修正提案のみ） |
| Google Slides | ○（PDF に書き出して評価） | 編集できるコネクタがあり、許可を得た場合のみ |

## インストール

### プラグインとして入れる

Claude Code で次を実行します。

```
/plugin install presentation --marketplace plageoj/claude-skills
```

### skill だけを入れる

```
git clone https://github.com/plageoj/claude-skills.git
ln -s "$PWD/claude-skills/plugins/presentation/skills/slide-review" ~/.claude/skills/slide-review
```

## 必要なもの

- Python 3 と [pymupdf](https://pypi.org/project/PyMuPDF/)（pptx の発表者ノートを読むには python-pptx も）
- 日本語フォント（例: `fonts-noto-cjk`）
- Marp を評価する場合: Node.js（npx）と Chrome
- pptx を評価する場合: LibreOffice

## 使い方

スライドのファイルや URL を渡して、発表時間・イベント名・聴衆と一緒に頼みます。

```
このスライドをレビューして。IoTLT で 5 分の LT、聴衆はエンジニアと学生です。 slides/iotlt.md
```

足りない情報は、評価の前に訊かれます。

## 自分のスタイルで使う

評価基準はすべて [`skills/slide-review/references/principal.md`](skills/slide-review/references/principal.md) にあります。このファイルを書き換えれば、自分のスタイルで評価できます。文字サイズの換算表やサムネイル判定の大きさなど、計測の基準もここで定義しています。

## 構成

```
skills/slide-review/
├── SKILL.md                 評価の手順
├── references/principal.md  スタイル定義（評価基準）
├── scripts/analyze.py       PDF・Marp・pptx の計測（文字サイズ、配色、コントラスト、サムネイルなど）
└── evals/                   skill のテストケース（入力スライドは同梱していません）
```
