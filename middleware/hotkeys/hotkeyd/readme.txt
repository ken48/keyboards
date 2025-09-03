Простой листенер хоткеев, альтернатива Karabiner-Elements.
Проблема карабинера в том, что он иногда пропускает модификатор option и печатает просто букву.
А так как я активно использую слои раскладок ОС, которые доступны через option или shift+option, то для меня это проблема.

Монитор работает как питоновский скрипт.
путь к конфигу с хоткеями и действиями должен быть в
~/.hotkeyd.json

Его можно как запускать в каждой сессии заново, так и зарегать в качестве демона.

1. Положи и настрой plist-файл

Путь: ~/Library/LaunchAgents/local.hotkeyd.plist

🔑 Обрати внимание:
путь к python (python) и путь к скрипту (/Users/kirill/projects/cvs/keyboards/middleware/hotkeys/hotkeyd/hotkeyd.py) должны быть именно те, что ты реально используешь;
в Accessibility/Input Monitoring нужно добавить именно этот бинарь python: /Users/kirill/.pyenv/bin/python

2. Подгрузи агент
В терминале:
launchctl bootout gui/$(id -u)/local.hotkeyd 2>/dev/null || true
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/local.hotkeyd.plist
launchctl kickstart -k gui/$(id -u)/local.hotkeyd  

3. Проверяй логи
tail -f /tmp/hotkeyd.out.log /tmp/hotkeyd.err.log
Там видно все print() и ошибки.

4. Управление

Остановить:
launchctl bootout gui/$(id -u)/local.hotkeyd

Запустить:
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/local.hotkeyd.plist

Перезапуск:
launchctl kickstart -k gui/$(id -u)/local.hotkeyd

Проверить статус:
launchctl list | grep hotkeyd
launchctl print gui/$(id -u)/local.hotkeyd | head -50
