/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: [
    "@loveworld-care/design-system",
    "@loveworld-care/domain-types",
    "@loveworld-care/api-contracts",
    "@loveworld-care/authorization",
    "@loveworld-care/audit",
  ],
  async rewrites() {
    const apiTarget =
      process.env.LW_API_INTERNAL_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      process.env.FASTAPI_BACKEND_URL ||
      "http://127.0.0.1:8000";
    return [
      {
        source: "/v1/:path*",
        destination: `${apiTarget}/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
