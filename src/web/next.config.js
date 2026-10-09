/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false,
  swcMinify: true,
  async rewrites() {
    let apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';
    apiBase = apiBase.replace(/\\/g, '');
    const cleanDestination = `${apiBase.replace(/\/api\/v1\/?$/, '')}/api/v1/:path*`;
    return [
      {
        source: '/api-ws/:path*',
        destination: cleanDestination
      }
    ];
  }
}

module.exports = nextConfig
