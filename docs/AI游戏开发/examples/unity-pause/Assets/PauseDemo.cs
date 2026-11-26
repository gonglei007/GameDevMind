using System;
using System.Collections;
using UnityEngine;

public sealed class PauseDemo : MonoBehaviour
{
    public bool IsPaused { get; private set; }
    public float GameSeconds { get; private set; }
    public float UiSeconds { get; private set; }
    public int Shots { get; private set; }
    public float ProjectilePosition { get; private set; } = 1f;
    private float previousTimeScale;

    private void Start()
    {
        var camera = gameObject.AddComponent<Camera>();
        camera.clearFlags = CameraClearFlags.SolidColor;
        camera.backgroundColor = new Color(0.10f, 0.13f, 0.17f);

        if (Array.IndexOf(Environment.GetCommandLineArgs(), "-pause-demo-check") >= 0)
            StartCoroutine(CheckPause());
    }

    private void Update()
    {
        UiSeconds += Time.unscaledDeltaTime;
        if (IsPaused)
            return;

        GameSeconds += Time.deltaTime;
        ProjectilePosition = Mathf.Min(1f, ProjectilePosition + 0.5f * Time.deltaTime);
    }

    private void SetPaused(bool paused)
    {
        if (paused == IsPaused)
            return;

        if (paused)
        {
            previousTimeScale = Time.timeScale;
            Time.timeScale = 0f;
        }
        else
        {
            Time.timeScale = previousTimeScale;
        }
        IsPaused = paused;
    }

    private void OnDisable() => SetPaused(false);

    private void Fire()
    {
        if (IsPaused)
            return;

        Shots++;
        ProjectilePosition = 0f;
    }

    private void RestartRound()
    {
        SetPaused(false);
        GameSeconds = 0f;
        Shots = 0;
        ProjectilePosition = 1f;
    }

    private void OnGUI()
    {
        GUILayout.BeginArea(new Rect(16, 16, Mathf.Min(Screen.width - 32, 560), 280), GUI.skin.box);
        GUILayout.Label("Pause Demo | " + (IsPaused ? "Paused" : "Running"));
        GUILayout.Label($"Game: {GameSeconds:F2}s   UI: {UiSeconds:F2}s   Shots: {Shots}");
        GUILayout.Label($"Patrol: {PatrolPosition:F2}   Projectile: {ProjectilePosition:F2}");
        DrawTrack("Patrol", PatrolPosition, Color.cyan);
        DrawTrack("Projectile", ProjectilePosition, new Color(1f, 0.75f, 0.35f));
        GUILayout.BeginHorizontal();
        if (GUILayout.Button(IsPaused ? "Resume" : "Pause"))
            SetPaused(!IsPaused);
        if (GUILayout.Button("Fire"))
            Fire();
        if (GUILayout.Button("Restart round"))
            RestartRound();
        GUILayout.EndHorizontal();
        GUILayout.EndArea();
    }

    private float PatrolPosition => Mathf.PingPong(GameSeconds / 2f, 1f);

    private static void DrawTrack(string label, float position, Color color)
    {
        GUILayout.Label(label);
        Rect track = GUILayoutUtility.GetRect(1f, 14f, GUILayout.ExpandWidth(true));
        Color oldColor = GUI.color;
        GUI.color = Color.gray;
        GUI.DrawTexture(track, Texture2D.whiteTexture);
        GUI.color = color;
        GUI.DrawTexture(new Rect(track.x + (track.width - 12f) * position, track.y, 12f, track.height),
            Texture2D.whiteTexture);
        GUI.color = oldColor;
    }

    private IEnumerator CheckPause()
    {
        // Start in slow motion to detect a hard-coded restore to 1.
        Time.timeScale = 0.5f;
        Fire();
        for (int cycle = 1; cycle <= 2; cycle++)
        {
            SetPaused(true);
            SetPaused(true);
            float gameBefore = GameSeconds;
            float uiBefore = UiSeconds;
            float projectileBefore = ProjectilePosition;
            int shotsBefore = Shots;
            Fire();
            yield return new WaitForSecondsRealtime(0.12f);
            if (!Require(Time.timeScale == 0f && Time.deltaTime == 0f &&
                         GameSeconds == gameBefore && ProjectilePosition == projectileBefore &&
                         Shots == shotsBefore && UiSeconds > uiBefore,
                         $"cycle {cycle}: gameplay frozen, fire ignored, UI clock advanced"))
                yield break;

            SetPaused(false);
            SetPaused(false);
            Fire();
            yield return new WaitForSecondsRealtime(0.12f);
            if (!Require(Time.timeScale == 0.5f && GameSeconds > gameBefore &&
                         Shots == shotsBefore + 1 && ProjectilePosition > 0f,
                         $"cycle {cycle}: original scale restored, gameplay and fire resumed"))
                yield break;
        }

        SetPaused(true);
        RestartRound();
        if (!Require(!IsPaused && Time.timeScale == 0.5f && GameSeconds == 0f &&
                     Shots == 0 && ProjectilePosition == 1f,
                     "restart while paused resets the round and restores scale"))
            yield break;

        SetPaused(true);
        enabled = false;
        if (Require(Time.timeScale == 0.5f, "disabling paused component restores scale"))
            Application.Quit(0);
    }

    private static bool Require(bool condition, string description)
    {
        if (condition)
            Debug.Log("PAUSE_DEMO PASS: " + description);
        else
        {
            Debug.LogError("PAUSE_DEMO FAIL: " + description);
            Application.Quit(1);
        }
        return condition;
    }
}
