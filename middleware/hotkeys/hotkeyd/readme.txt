Простой листенер хоткеев, альтернатива Karabiner-Elements.
Проблема карабинера в том, что он иногда пропускает модификатор option и печатает просто букву.
А так как я активно использую слои раскладок ОС, которые доступны через option или shift+option, то для меня это проблема.

Монитор работает как питоновский скрипт.
путь к конфигу с хоткеями и действиями должен быть в
~/.hotkeyd.json

Его можно как запускать в каждой сессии заново, так и зарегать в качестве демона.

1. Создай plist-файл

Путь: ~/Library/LaunchAgents/local.hotkeyd.plist

Содержимое:
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>local.hotkeyd</string>

  <key>ProgramArguments</key>
  <array>
    <string>python</string>
    <string>/Users/kirill/projects/cvs/keyboards/middleware/hotkeys/hotkeyd/hotkeyd.py</string>
  </array>

  <!-- запускать при входе -->
  <key>RunAtLoad</key>
  <true/>

  <!-- перезапускать при падении -->
  <key>KeepAlive</key>
  <true/>

  <!-- чтобы точно стартовал в GUI-сессии -->
  <key>LimitLoadToSessionType</key>
  <string>Aqua</string>

  <!-- чтобы скрипту хватало PATH -->
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/Users/kirill/.pyenv/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>

  <!-- куда писать логи -->
  <key>StandardOutPath</key>
  <string>/tmp/hotkeyd.out.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/hotkeyd.err.log</string>
</dict>
</plist>

🔑 Обрати внимание:
путь к python (python) и путь к скрипту (/Users/kirill/projects/cvs/keyboards/middleware/hotkeys/hotkeyd/hotkeyd.py) должны быть именно те, что ты реально используешь;
в Accessibility/Input Monitoring нужно добавить именно этот бинарь python: /Users/kirill/.pyenv/bin/python

2. Подгрузи агент
В терминале:
launchctl unload ~/Library/LaunchAgents/local.hotkeyd.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/local.hotkeyd.plist
launchctl start local.hotkeyd

3. Проверяй логи
tail -f /tmp/hotkeyd.out.log /tmp/hotkeyd.err.log
Там видно все print() и ошибки.

4. Управление
Остановить:
launchctl stop local.hotkeyd
Убрать из автозагрузки:
launchctl unload ~/Library/LaunchAgents/local.hotkeyd.plist

👉 Таким образом, hotkeyd будет стартовать автоматически при входе твоего пользователя в macOS и работать постоянно в фоне.
Хочешь, я дополню примером shell-скрипта для перезапуска hotkeyd руками (удобный алиас)?