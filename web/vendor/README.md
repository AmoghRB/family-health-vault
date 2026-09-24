# web/vendor/ (owner: Frontend, API & Demo role)

Third-party files served locally so the demo works **with Wi-Fi off**.

Download once and commit it:

```bash
curl -L -o web/vendor/chart.umd.min.js https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js
```

Don't load Chart.js (or anything else) from a CDN in `index.html`. The judges'
demo runs offline.
