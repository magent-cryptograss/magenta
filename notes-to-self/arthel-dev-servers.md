# Arthel Dev Servers on Hunter

## Starting the dev servers in justin-arthel container

### Fix git ownership first (needed after container restart):
```bash
docker exec -u magent justin-arthel git config --global --add safe.directory /home/magent/workspace/arthel
```

### Clear old output and start justinholmes.com (port 4000 → 14000):
```bash
docker exec justin-arthel rm -rf /home/magent/workspace/arthel/output/_prebuild_output
docker exec -d -u magent justin-arthel bash -c "cd /home/magent/workspace/arthel && npm run dev:jh > /tmp/arthel-jh.log 2>&1"
```

### Start cryptograss.live (port 4001 → 14001):
```bash
docker exec -d -u magent justin-arthel bash -c "cd /home/magent/workspace/arthel && npm run dev:cg > /tmp/arthel-cg.log 2>&1"
```

## URLs
- justinholmes.com: https://arthel.justin.hunter.cryptograss.live (or justin0.hunter.cryptograss.live)
- cryptograss.live: https://justin1.hunter.cryptograss.live
- Oracle: https://justin1.hunter.cryptograss.live/tools/oracle-of-bluegrass-bacon.html

## Node Version Workaround

The container has Node 18, but arthel uses `import ... with { type: 'json' }` which requires Node 20+.

**Use npx to run with Node 22:**
```bash
cd /home/magent/workspace/arthel
npx -y node@22 ./node_modules/.bin/webpack serve --config src/build_logic/webpack.cryptograss.dev.js --port 4003
```

This downloads Node 22 on first run (cached after), then runs webpack with it.

**Quick one-liner for previews:**
```bash
cd /home/magent/workspace/arthel && npx -y node@22 ./node_modules/.bin/webpack serve --config src/build_logic/webpack.cryptograss.dev.js --port 4003 &
```

Port mapping:
- 4003 → justin3.hunter.cryptograss.live
- 4004 → justin4.hunter.cryptograss.live
- etc.

## Known Issues
- First build sometimes 404s on HTML files - rebuild usually fixes it
- If port in use error, kill orphaned webpack: `docker exec justin-arthel pkill -9 -f "webpack.*cryptograss"`

