# presentation

ぺんた（@plageoj）のプレゼンテーションスタイルでスライドを扱う Claude Code の skill です。

| skill | 内容 |
|:--|:--|
| slide-review | 完成したスライドをこのスタイルに照らして評価し、修正提案と自動修正を行う |
| slide-create | ドキュメント・台本・既存のスライドから、このスタイルの Marp スライドを作る。載せきれない情報は発表者ノートに移し、元にない情報は足さない |

## slide-review

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

## slide-create

ドキュメント（Markdown・PDF・Google Docs など）、台本、既存のスライド（PDF・pptx・Google Slides・Marp）を読み、同梱の Marp テーマ（`assets/penta.css`）でこのスタイルのスライドを作ります。元との対応表を作り、元の情報がすべて新しいページか発表者ノートに残っていることを確かめます。仕上げに yomiyasu で文言を推敲し、slide-review で評価して直します。

```
このスライド（lecture.pdf）をぺんたスタイルで作り直して。15 分の講義、聴衆は中学生です。
```

```
この記事（docs/design.md）を、ぺんたスタイルで 5 分の LT のスライドにして。聴衆はエンジニアです。
```

「ぺんたスタイルで」とスタイルを名指ししたときだけ使われます。名指ししない「スライドにして」は、Claude のスライドデッキ機能などに任されます。出力は Marp だけです。

作り直したスライドは、video プラグインの intro-video でそのまま動画にできます。

## インストール

文言の推敲に [yomiyasu](https://github.com/nanaism/yomiyasu) プラグインを使います。presentation プラグインの依存として自動で入りますが、先に yomiyasu のマーケットプレイスを登録しておく必要があります。

```
/plugin marketplace add nanaism/yomiyasu
```

### プラグインとして入れる

Claude Code で次を実行します。

```
/plugin install presentation --marketplace plageoj/claude-skills
```

### skill だけを入れる

```
git clone https://github.com/plageoj/claude-skills.git
ln -s "$PWD/claude-skills/plugins/presentation/skills/slide-review" ~/.claude/skills/slide-review
ln -s "$PWD/claude-skills/plugins/presentation/skills/slide-create" ~/.claude/skills/slide-create
```

slide-create は slide-review のスタイル定義と計測スクリプトを使うので、両方を入れてください。yomiyasu は自動で入らないので、[yomiyasu の README](https://github.com/nanaism/yomiyasu) に従って別に入れてください。

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

評価基準と、資料からスライドを作るときの決まりはすべて [`skills/slide-review/references/principal.md`](skills/slide-review/references/principal.md) にあります。このファイルと slide-create の Marp テーマ（`skills/slide-create/assets/penta.css`）を書き換えれば、自分のスタイルで評価し、スライドを作れます。文字サイズの換算表やサムネイル判定の大きさなど、計測の基準もここで定義しています。

## 構成

```
skills/slide-review/
├── SKILL.md                 評価の手順
├── references/principal.md  スタイル定義（評価基準）
├── scripts/analyze.py       PDF・Marp・pptx の計測（文字サイズ、配色、コントラスト、サムネイルなど）
└── evals/                   skill のテストケース（入力スライドは同梱していません）
skills/slide-create/
├── SKILL.md                 資料からスライドを作る手順
└── assets/penta.css         Marp テーマ
```
