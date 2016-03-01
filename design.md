Orizon Hub
==========

## Message Bus

* Command processor
  * routing: Command name, Protocol
* Logger
  * `logging`
  * SQLite
* Forwarder
  * rules

## Protocol Plugins

* Telegram bot
  * polling (thread)
  * sending queue (workers)
* Telegram cli
  * callback (thread)
  * sending queue (thread)
* IRC
  * polling (thread)
  * sending queue (thread)
* HTTP server
  * uWSGI
* Websocket
  * uWSGI

## Command Plugins

* Simple text (233)
* Log search (m, search, quote)
* NLP stuff (say, reply)
* External API

## Message Object

```sql
CREATE TABLE IF NOT EXISTS messages (
	id INTEGER PRIMARY KEY,
	protocol TEXT NOT NULL,
	pid INTEGER, -- protocol-specified id
	src INTEGER, -- sender id
	text TEXT,
	media TEXT,
	time INTEGER,
	fwd_src INTEGER,
	fwd_time INTEGER,
	reply_id INTEGER,
	FOREIGN KEY(src) REFERENCES users(id)
)
```

## Users

**REPLACE INTO**.

```sql
CREATE TABLE IF NOT EXISTS users (
	id INTEGER PRIMARY KEY,
	protocol TEXT NOT NULL,
	type INTEGER NOT NULL,
	pid INTEGER, -- protocol-specified id
	username TEXT,
	first_name TEXT,
	last_name TEXT,
	alias TEXT
)
```

```python
class UserType(enum.IntEnum):
    user = 1
    group = 2
    # to be compatible with tg-cli
    channel = 5
```

## Message Path

```
   v----------------------------------------.
Telegram --post_async-\        /-Forwarder--+
IRC      --post_async--->Bus-->--Logger--v  |
HTTP     --post------+/   ^    \-Command processor
         <-return----'    |_________________/
```
