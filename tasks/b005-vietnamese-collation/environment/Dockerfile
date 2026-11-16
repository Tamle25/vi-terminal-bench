FROM node:22.14.0-bookworm-slim@sha256:1c18d9ab3af4585870b92e4dbc5cac5a0dc77dd13df1a5905cea89fc720eb05b AS node_runtime
RUN mkdir /runtime && cp -L /usr/lib/x86_64-linux-gnu/libstdc++.so.6 /usr/lib/x86_64-linux-gnu/libgcc_s.so.1 /runtime/
FROM python:3.12.12-slim-bookworm@sha256:593bd06efe90efa80dc4eee3948be7c0fde4134606dd40d8dd8dbcade98e669c
COPY --from=node_runtime /usr/local/bin/node /usr/local/bin/node
COPY --from=node_runtime /runtime/ /usr/local/lib/
RUN ldconfig && node -e "require('fs').writeFileSync('/opt/collation-runtime.json',JSON.stringify({node:process.versions.node,icu:process.versions.icu,cldr:process.versions.cldr,unicode:process.versions.unicode,collator:new Intl.Collator('vi',{usage:'sort',sensitivity:'variant',caseFirst:'lower',numeric:false,ignorePunctuation:false}).resolvedOptions()}))"
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8 TZ=Asia/Ho_Chi_Minh PYTHONUTF8=1
WORKDIR /app
COPY generate_fixture.py fixture.json /tmp/
RUN python /tmp/generate_fixture.py && rm /tmp/generate_fixture.py /tmp/fixture.json
