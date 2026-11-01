/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: [
    "@loveworld-care/design-system",
    "@loveworld-care/domain-types",
    "@loveworld-care/api-contracts",
    "@loveworld-care/authorization",
    "@loveworld-care/audit",
    "@loveworld-care/fhir-adapters",
  ],
};

export default nextConfig;
