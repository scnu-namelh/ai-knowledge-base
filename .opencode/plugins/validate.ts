import type { PluginModule } from "@opencode-ai/plugin";

export default {
  server: async ({ $, directory }) => {
    return {
      "tool.execute.after": async (input, output) => {
        const { tool, args } = input;
        if (tool !== "write" && tool !== "edit") return;

        const filePath: unknown = args.file_path ?? args.filePath;
        if (typeof filePath !== "string") return;
        if (!filePath.startsWith("knowledge/articles/") || !filePath.endsWith(".json")) return;

        const absPath = `${directory}/${filePath}`;

        try {
          const result = await $`python3 hooks/validate_json.py ${absPath}`.nothrow();
          if (result.exitCode === 0) return;

          const stderr = result.stderr?.toString() ?? "";
          const stdout = result.stdout?.toString() ?? "";
          output.metadata = {
            ...(output.metadata ?? {}),
            validation: "failed",
            validation_errors: (stderr || stdout).trim(),
          };
        } catch (err) {
          output.metadata = {
            ...(output.metadata ?? {}),
            validation: "error",
            validation_error: err instanceof Error ? err.message : String(err),
          };
        }
      },
    };
  },
} satisfies PluginModule;
