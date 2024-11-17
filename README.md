# hems-exporter

[ブログ記事も見てね](https://minokavva.room4.dev/blog/20231206_advent_calenter_2023_echonet/)

```
$ docker build -t hems-exporter .

# use --net=host for UDP multicast
$ docker run -d --restart=always --net=host hems-exporter
```
