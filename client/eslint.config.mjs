import { dirname } from "node:path"
import { fileURLToPath } from "node:url"
import { FlatCompat } from "@eslint/eslintrc"

const __dirname = dirname(fileURLToPath(import.meta.url))
const compat = new FlatCompat({ baseDirectory: __dirname })

// `next lint` is deprecated as of Next 15.5; this is the ESLint CLI setup it
// migrates to. eslint-config-next 15 ships legacy configs, hence FlatCompat.
const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    ignores: [
      ".next/**",
      "out/**",
      "build/**",
      "next-env.d.ts",
      // Generated shadcn/ui primitives; not hand-maintained.
      "components/ui/**",
    ],
  },
]

export default eslintConfig
