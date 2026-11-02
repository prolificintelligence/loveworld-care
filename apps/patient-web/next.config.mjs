/** @type {import('next').NextConfig} */
const apiBase =
  process.env.LW_API_INTERNAL_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://127.0.0.1:8000";

const nextConfig = {
  transpilePackages: [
    "@loveworld-care/design-system",
    "@loveworld-care/domain-types",
    "@loveworld-care/api-contracts",
  ],
  async rewrites() {
    return [
      {
        source: "/v1/:path*",
        destination: `${apiBase}/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
