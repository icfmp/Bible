# GitHub Wiki publishing

The public wiki is the **actual GitHub Wiki** at https://github.com/icfmp/Bible/wiki, not the `wiki/` folder displayed in the source repository.

The Markdown files in `wiki/` are the canonical source. The workflow `.github/workflows/publish-wiki.yml` copies them into the wiki's separate Git repository.

## One-time setup (repository owner)

1. In the GitHub repository settings, make sure **Wikis** is enabled. Open the public wiki and create its first page if it has never been initialized; otherwise the `Bible.wiki.git` clone may fail.
2. Create a GitHub personal access token authorized to **push to the wiki Git repository**. A classic PAT with `repo` scope can be used for a private repository; for a public repository a classic token with `public_repo` scope may suffice. Use a dedicated token with the least privileges available. GitHub fine-grained PAT wiki Git support may vary; test before relying on it.
3. Save it as repository Actions secret **`WIKI_PUSH_TOKEN`** under **Settings → Secrets and variables → Actions**. Never commit the token.
4. Set repository Actions variable **`BIBLE_WIKI_SYNC_ENABLED`** to `1` in the same settings area.
5. Merge the documentation PR. Run **Actions → Publish GitHub Wiki → Run workflow** once, or push a change to `wiki/` on `main`.
6. Check https://github.com/icfmp/Bible/wiki to verify that the pages and sidebar were published.

The workflow will skip publishing until the enable variable is set. It fails with a clear error if the token is missing after enabling.

## Maintenance

Edit pages under `wiki/` in the main repository. Once merged to `main`, the workflow publishes the Markdown to the real GitHub wiki.

Only files from `wiki/*.md` are copied. Unrelated wiki files are preserved; deleting a source page does not automatically delete its already published wiki counterpart.

The wiki repository is separate from the main GitHub API, which is why a publishing workflow and token are needed.
