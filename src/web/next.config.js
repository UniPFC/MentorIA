/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false,
  swcMinify: true,
  async rewrites() {
    return [
      {
        source: '/api-ws/:path*',
        destination: process.env.NEXT_PUBLIC_API_BASE_URL 
          ? `${process.env.NEXT_PUBLIC_API_BASE_URL.replace('/api/v1', '')}/api/v1/:path*`
          : 'http://localhost:8000/api/v1/:path*'
      }
    ];
  }
}

module.exports = nextConfig
