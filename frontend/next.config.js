/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  // remove to call backend directly
  /*async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.API_BACKEND_URL}/api/:path*`,
      },
    ];
  },*/
};

module.exports = nextConfig;
