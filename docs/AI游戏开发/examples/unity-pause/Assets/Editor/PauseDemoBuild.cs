using System;
using System.IO;
using UnityEditor;
using UnityEditor.Build.Reporting;

public static class PauseDemoBuild
{
    public static void BuildWindows()
    {
        Directory.CreateDirectory("Builds");
        var report = BuildPipeline.BuildPlayer(
            new[] { "Assets/PauseDemo.unity" },
            "Builds/PauseDemo.exe",
            BuildTarget.StandaloneWindows64,
            BuildOptions.Development);

        if (report.summary.result != BuildResult.Succeeded)
            throw new InvalidOperationException($"Pause demo build: {report.summary.result}");
    }
}
