/** @type {import('next').NextConfig} */
const nextConfig = {
  // Fail the build on type or lint errors instead of shipping them.
  eslint: {
    ignoreDuringBuilds: false,
  },
  typescript: {
    ignoreBuildErrors: false,
  },
  images: {
    unoptimized: true,
  },
  // Routes from the earlier learner/instructor design.
  async redirects() {
    return [
      { source: "/learner", destination: "/dashboard", permanent: true },
      { source: "/instructor/:path*", destination: "/dashboard", permanent: true },
    ]
  },
}

export default nextConfig
