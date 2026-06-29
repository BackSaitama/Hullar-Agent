# Contributing to HULLAR

Thanks for your interest in improving HULLAR! 🎉

## 🐛 Reporting bugs
Open an issue using the **Bug report** template. Include:
- What you typed (the command)
- What happened vs. what you expected
- Your AI backend (Ollama / Gemini / etc.) and OS
- Relevant lines from `data/hullar.log` (the bot's log)

## 💡 Suggesting features
Open an issue with the **Feature request** template and describe the use case.

## 🔧 Adding a new skill
Most skills are tiny. The pattern:

1. **Write the function** in a module under `actions/` — it takes `parameters: dict` and returns a string:
   ```python
   def my_skill(parameters: dict | None = None) -> str:
       return "done!"
   ```
2. **Register one regex rule** in `actions/dispatcher.py` (`_RULES`):
   ```python
   ([r"\bmy keyword\b"], my_skill, _empty),
   ```
3. **Keep it tolerant** — match typos and Turkish suffixes (use `\w*`, not a hard `\b` at the end).
4. **For English/other languages**, add keywords to `_MULTI_TR` in `dispatcher.py` so they route instantly.

## ✅ Before opening a PR
- Run an import/syntax check: `python -c "from actions import ActionDispatcher; ActionDispatcher()"`
- Make sure you didn't commit secrets (`.env`, `data/telegram.json` are git-ignored — keep it that way)
- Keep commits focused and messages clear

## 🔒 Security
Never commit API keys, bot tokens, or personal data. If you find a security issue,
please open an issue marked **security** (or contact the maintainer privately).

Happy hacking! 🚀
