# claude-skills

plageoj が作った Claude Code のプラグインと skill を集めたマーケットプレイスです。

## プラグイン

| プラグイン | 内容 |
|:--|:--|
| [presentation](plugins/presentation/) | 完成したスライドを、ぺんた（@plageoj）のプレゼンテーションスタイルに照らして評価し、修正提案と自動修正を行う |
| [video](plugins/video/) | ブラウザで動くアプリのデモやスライドを素材に、ナレーションと字幕付きの紹介動画を作る（台本・収録・VO・Remotion での編集・公開前の確認） |

## インストール

プラグインごとに入れます。

```
/plugin install presentation --marketplace plageoj/claude-skills
```

マーケットプレイスとして登録して、一覧から選ぶこともできます。

```
/plugin marketplace add plageoj/claude-skills
```

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
