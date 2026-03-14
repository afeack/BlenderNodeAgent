# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) (or [oxc](https://oxc.rs) when used in [rolldown-vite](https://vite.dev/guide/rolldown)) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```


{
  "protocol": "BLENDER_NODE_AGENT",
  "version": "2.0",
  "timestamp": 1772977264697,
  "material_data": {
    "material_name": "Complex_Metallic_Marble_Glass",
    "nodes": [
      {
        "node_id": "output",
        "node_type": "ShaderNodeOutputMaterial",
        "properties": []
      },
      {
        "node_id": "mix_shader",
        "node_type": "ShaderNodeMixShader",
        "properties": [
          {
            "name": "Fac",
            "value": 0.7
          }
        ]
      },
      {
        "node_id": "principled_marble",
        "node_type": "ShaderNodeBsdfPrincipled",
        "properties": [
          {
            "name": "Base Color",
            "value": [
              0.05,
              0.05,
              0.05,
              1
            ]
          },
          {
            "name": "Metallic",
            "value": 0.9
          },
          {
            "name": "Roughness",
            "value": 0.15
          },
          {
            "name": "Subsurface Weight",
            "value": 0.15
          }
        ]
      },
      {
        "node_id": "principled_glass",
        "node_type": "ShaderNodeBsdfPrincipled",
        "properties": [
          {
            "name": "Base Color",
            "value": [
              1,
              1,
              1,
              1
            ]
          },
          {
            "name": "Transmission Weight",
            "value": 0.5
          },
          {
            "name": "Roughness",
            "value": 0.4
          },
          {
            "name": "IOR",
            "value": 1.48
          },
          {
            "name": "Alpha",
            "value": 0.8
          }
        ]
      },
      {
        "node_id": "noise_texture",
        "node_type": "ShaderNodeTexNoise",
        "properties": [
          {
            "name": "Scale",
            "value": 10
          },
          {
            "name": "Detail",
            "value": 3
          },
          {
            "name": "Roughness",
            "value": 0.5
          },
          {
            "name": "Lacunarity",
            "value": 2
          }
        ]
      },
      {
        "node_id": "color_ramp_marble",
        "node_type": "ShaderNodeValToRGB",
        "properties": [
          {
            "name": "Color",
            "value": [
              [
                0,
                0,
                0,
                1
              ],
              [
                0.1,
                0.1,
                0.1,
                1
              ]
            ]
          }
        ]
      },
      {
        "node_id": "wave_texture",
        "node_type": "ShaderNodeTexWave",
        "properties": [
          {
            "name": "Scale",
            "value": 5
          },
          {
            "name": "Distortion",
            "value": 1.5
          },
          {
            "name": "Detail",
            "value": 2
          }
        ]
      },
      {
        "node_id": "color_ramp_scratch",
        "node_type": "ShaderNodeValToRGB",
        "properties": [
          {
            "name": "Color",
            "value": [
              [
                0,
                0,
                0,
                1
              ],
              [
                1,
                1,
                1,
                1
              ]
            ]
          }
        ]
      },
      {
        "node_id": "bump_node",
        "node_type": "ShaderNodeBump",
        "properties": [
          {
            "name": "Strength",
            "value": 0.4
          },
          {
            "name": "Distance",
            "value": 0.5
          }
        ]
      },
      {
        "node_id": "fresnel_node",
        "node_type": "ShaderNodeFresnel",
        "properties": [
          {
            "name": "IOR",
            "value": 1.45
          }
        ]
      }
    ],
    "connections": [
      {
        "from_node": "noise_texture",
        "from_socket": "Factor",
        "to_node": "color_ramp_marble",
        "to_socket": "Factor"
      },
      {
        "from_node": "color_ramp_marble",
        "from_socket": "Color",
        "to_node": "principled_marble",
        "to_socket": "Base Color"
      },
      {
        "from_node": "wave_texture",
        "from_socket": "Color",
        "to_node": "color_ramp_scratch",
        "to_socket": "Factor"
      },
      {
        "from_node": "color_ramp_scratch",
        "from_socket": "Color",
        "to_node": "bump_node",
        "to_socket": "Height"
      },
      {
        "from_node": "bump_node",
        "from_socket": "Normal",
        "to_node": "principled_marble",
        "to_socket": "Normal"
      },
      {
        "from_node": "principled_marble",
        "from_socket": "BSDF",
        "to_node": "mix_shader",
        "to_socket": "Shader"
      },
      {
        "from_node": "principled_glass",
        "from_socket": "BSDF",
        "to_node": "mix_shader",
        "to_socket": "Shader"
      },
      {
        "from_node": "fresnel_node",
        "from_socket": "Factor",
        "to_node": "mix_shader",
        "to_socket": "Fac"
      },
      {
        "from_node": "mix_shader",
        "from_socket": "Shader",
        "to_node": "output",
        "to_socket": "Surface"
      }
    ]
  }
}