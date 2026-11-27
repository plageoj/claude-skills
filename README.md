# claude-skills

plageoj が作った Claude Code のプラグインと skill を集めたマーケットプレイスです。

## プラグイン

| プラグイン | 内容 |
|:--|:--|
| [presentation](plugins/presentation/) | 完成したスライドを、ぺんた（@plageoj）のプレゼンテーションスタイルに照らして評価し、修正提案と自動修正を行う。ドキュメント・台本・既存のスライドから、このスタイルの Marp スライドを作る |
| [video](plugins/video/) | ブラウザで動くアプリのデモやスライドを素材に、ナレーションと字幕付きの紹介動画を作る（台本・収録・VO・Remotion での編集・公開前の確認） |

## インストール

Claude Code で、このマーケットプレイスと、依存する [yomiyasu](https://github.com/nanaism/yomiyasu) のマーケットプレイスを登録してから、プラグインごとに入れます。yomiyasu は依存として自動で入ります。

```
/plugin marketplace add nanaism/yomiyasu
/plugin marketplace add plageoj/claude-skills
/plugin install presentation@plageoj
/plugin install video@plageoj
```

`/plugin` だけを実行すると、登録したマーケットプレイスの一覧から選んで入れることもできます。

## 構成

```
.claude-plugin/marketplace.json   マーケットプレイスの定義
plugins/<プラグイン名>/
├── .claude-plugin/plugin.json
├── README.md
└── skills/<skill 名>/SKILL.md
```

プラグインを追加するときは `plugins/` にディレクトリを作り、`marketplace.json` の `plugins` に登録します。

## ライセンス

MIT
