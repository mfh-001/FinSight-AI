# Running FinSight for a team of 5 to 50 people

One server, one copy of the app, documents stay on that server.

What is tested and what is not:

- Tested on a laptop: the app, the password login (wrong password rejected, right one accepted), retention and delete.
- Not tested here: the Docker images and the GPU profile. I had no Docker and no GPU. Treat the compose file as a starting point and check it on your server first.

## 1. Pick the hardware

| Need | Hardware | Notes |
|---|---|---|
| Search, extraction to Excel, risk check | Any small server, 2 CPU cores, 4 GB RAM | No model needed. This is the default `none` backend. |
| Written answers from a model | One 24 GB GPU (for example an RTX 4090 or A5000) | Run a vLLM server with Qwen2.5-VL-7B-Instruct-AWQ. The `gpu` compose profile does this. |
| Written answers, no GPU | A CPU box with Ollama or llama.cpp and a small model | Slower. A 1.5B to 3B model is about what a CPU can do. |

Reading the pages is quick. Sizes are what you should watch: a 100 page filing takes tens of seconds to read the first time.

## 2. Start it

With Docker:

```bash
git clone https://github.com/mfh-001/FinSight-AI
cd FinSight-AI
cp .env.example .env     # then edit it
docker compose --profile cpu up -d
```

Without Docker:

```bash
pip install ".[app]"
FINSIGHT_PERSIST=1 FINSIGHT_HOME=/srv/finsight FINSIGHT_HOST=0.0.0.0 finsight serve --port 7860
```

## 3. Passwords

Set one shared login with an environment variable:

```bash
FINSIGHT_AUTH=firm:a-long-password
```

That is a single account. For one account per person, put the app behind a reverse proxy
(Caddy or nginx) that does basic auth or single sign-on, and keep port 7860 closed to everything else.
Always serve it over HTTPS if it is reachable beyond your office network.

## 4. Shared library or private sessions

- Default: each visitor gets a private temporary folder. It is deleted when their session ends or after one hour.
- `FINSIGHT_PERSIST=1`: all visitors share one library in `FINSIGHT_HOME`. Everyone who can log in can see every file. Use this only when that is what you want.

## 5. How long files are kept

```bash
FINSIGHT_RETENTION_DAYS=30
```

Files older than that are deleted the next time the app or the command line starts. `0` keeps files until someone deletes them.
Delete by hand:

```bash
finsight delete some-file.pdf
finsight delete --all
```

## 6. Backups

In shared mode the library is the folder `FINSIGHT_HOME` (the `finsight-data` volume in Docker).
It holds a copy of each PDF and the text read from it. Back that folder up like any other client data:

```bash
tar czf finsight-$(date +%F).tgz -C /srv/finsight .
```

Restore by unpacking into an empty `FINSIGHT_HOME`. Test a restore once before you rely on it.
Backups are as sensitive as the originals. Encrypt them and apply the same retention.

## 7. What leaves the server

Nothing, unless you point `FINSIGHT_LLM_BASE_URL` at a remote model server. With the `none` backend, or a model
server on the same machine or your own network, no document text is sent anywhere.
Check your firewall rules if you need to be able to say that to a client.

## 8. Limits you should know about

- Answers from a model can be wrong. Every answer shows its page so a person can check it.
- Scanned pages have no text layer. They need the vision model path, which needs a GPU.
- There is no per-user audit log yet. If you need one, the reverse proxy access log is the closest thing today.
