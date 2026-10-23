import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    // Las publicaciones llevan una imagen de hasta 4 MB: el limite por defecto de las acciones (1 MB) no alcanza.
    // 4,5 MB es el maximo que admite una funcion de Vercel; la accion valida ademas que la imagen no pase de 4 MB.
    serverActions: { bodySizeLimit: "4.5mb" },
  },
};

export default nextConfig;
