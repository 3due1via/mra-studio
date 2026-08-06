FROM node:22-alpine

WORKDIR /workspace

RUN corepack enable     && corepack prepare pnpm@10.15.0 --activate

COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY apps/mra-studio/package.json apps/mra-studio/package.json

RUN pnpm install --filter @mra/studio... --frozen-lockfile

COPY apps/mra-studio apps/mra-studio

EXPOSE 5173

CMD ["pnpm", "--filter", "@mra/studio", "dev", "--host", "0.0.0.0"]
