# Graph Report - silent-mode-backend  (2026-11-24)

## Corpus Check
- 243 files · ~227,134 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 12 file(s) not represented in the graph (top: (none) 4, .mdc 1, .pbxproj 1)

## Summary
- 5539 nodes · 12986 edges · 229 communities (132 shown, 97 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 1380 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `5e69f9d5`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Tool
- nova_controller.py
- SimpleFinancesService
- text
- TranscribeSocketTests
- OpenAILoopTests
- ServerEvent
- AgentLoopImageTests
- test_background_agent.py
- ._env
- make_update
- ClaudeService
- GithubService
- build_service
- Nova system prompt (persona)
- SidekickController
- agent_loop.py
- Harness
- CodingService
- ScheduledTaskService
- _most_recent_local_midnight_utc
- FakeChunkDao
- time
- test_memory_chunk_service.py
- meeting_controller.py
- CursorService
- MeetingService
- FileOperationTests
- AppModel
- UpdateDeliveryService
- ConversationController
- Keys
- deploy_main.py
- NovaSession
- LiveReply
- auth_service.py
- SessionManager
- _runner
- _silent_logger
- json
- DATGlassesCamera
- Handle
- CodeService
- ResponsibilityService
- Responsibility
- McpOAuthService
- make_update
- build_service
- asyncio
- call_controller.py
- McpServerService
- AgentLoop
- TurnTimer
- build_app
- AuthService
- SpeakOnCompletionTests
- build_service
- FakeMessage
- FakePersonaDao
- ConversationLoopStreamTests
- sms_controller.py
- SpeechPlayer
- EndpointDecisionTests
- .look
- FakeCamera
- ConversationControllerTests
- ._artifact_for_tool
- BaseDao
- ClientEvent
- NovaGlasses
- Conversation
- test_vision.py
- McpServer
- PersonaService
- TwilioService
- HttpGateTests
- ._conversation_turn
- run_migrations.py
- IsIdleTests
- parse_gate_reply
- is_nova_interrupt_phrase
- fake_stream
- LiveScreenTests
- FakeMcpServerDao
- FakeMeetingDao
- CrudTests
- SettingsService
- Person
- bip_service.py
- test_responsibility_service.py
- StreamedSpeechTests
- test_deploy_main.py
- test_memory_injection.py
- meeting_service.py
- ASRService
- main.py
- UpdateService
- Mac code agent daemon
- test_spoken_reply.py
- SpokenProse
- recording_meeting
- ._run_begin
- BipService
- NovaSocket
- Rig
- asr_service.py
- test_sms.py
- CompletionNotificationTests
- ElevenLabsService
- .repair_tool_pairing
- .deploy_main
- FakeDao
- .run_turn
- protocol.py
- HomeView
- asr-bench.py
- test_conversation_loop.py
- SpeakQueuedLinesGatingTests
- APIClient
- Foundation
- Earcon
- SidekickSocketTests
- AuthStore
- EndSessionTests
- SidekickSession
- worker.py
- DeployService
- CheckForStaleConversationsTests
- FollowUpTests
- GateTestCase
- ClassificationTests
- ProviderSelectionTests
- CaptureEngine
- AuthenticateTests
- history_compaction.py
- AsrLock
- SidekickConnection
- WorkingTreeTests
- AudioRouteManager
- .isOnlyWakePhrase
- VoiceMode
- .sanitize_mcp_history
- PerformTests
- FakeDao
- SilentModeServiceTests
- .split_sms_body
- .allowed_sms_senders
- FakeSendWebSocket
- FallbackChainTests
- SpokenTrackTests
- ConversationControllerSilentModeTests
- GlassesSocketTests
- VisionService
- test_asr_filters.py
- MemoryChunkService
- replay_request.py
- host_environment_prompt.py
- PassSentinelTests
- TTSService
- CLAUDE.md
- .decode
- install.sh
- uninstall.sh
- settings_controller.py
- nova-backend
- worktree.py
- CurrentModelTests
- FakeHttp
- CommandLineService
- ToolServiceTests
- meeting_socket
- dict
- RelayTokenTests
- SpeechWakeDetector
- SentryModeTests
- MirrorTests
- AddPersonView
- PersonaPrompt
- .setUp
- CreateScheduleRequirementTests
- AmbientForwardingTests
- os
- row_to_session
- SelfKillHazardTests
- SpawnStaleAncestorHelperTimingTests
- HostEnvironmentPromptTests
- MacSessionLifecycleTests
- ThinkingPulseTests
- .wantsToSee
- GoodbyeTimingTests
- String
- InterruptedToolCallTests
- CooldownTests
- speech_summary
- LockoutTests
- GuardrailTests
- ToolUseStarted
- FakeConversationService
- FakeAgentLoop
- FakeClaudeService
- FaceService
- AgentLink
- _FakeTable
- clamp_spoken
- FakeNotesDao
- FakeResponse
- FinishedSessionTowerTests
- ReplyQueue
- MeetingSegment
- FallbackTests
- AuthenticationTests
- FakeConversationDao
- FakeEmbeddingService
- FakeUpdateService
- make_request
- WorktreeCollisionTests
- ResponsibilityDeliveryTests
- Entry
- ReportMediumTests
- _said
- ServiceMethodToolConfig

## God Nodes (most connected - your core abstractions)
1. `AgentLoop` - 135 edges
2. `Conversation` - 92 edges
3. `ConversationController` - 85 edges
4. `ToolService` - 72 edges
5. `build_service()` - 57 edges
6. `CodingService` - 55 edges
7. `Responsibility` - 54 edges
8. `MeetingService` - 52 edges
9. `UpdateService` - 50 edges
10. `Tool` - 48 edges

## Surprising Connections (you probably didn't know these)
- `Server behaviour` --references--> `audio_file_bytes()`  [INFERRED]
  SIDEKICK_PROTOCOL.md → src/controller/audio_ws.py
- `Server → client` --references--> `stream_tts_audio()`  [INFERRED]
  SIDEKICK_PROTOCOL.md → src/controller/nova_controller.py
- `Server behaviour` --references--> `AgentLoop`  [INFERRED]
  SIDEKICK_PROTOCOL.md → src/harness/agent_loop.py
- `Server behaviour` --references--> `ClaudeService`  [INFERRED]
  SIDEKICK_PROTOCOL.md → src/service/claude_service.py
- `Tests` --references--> `is_nova_interrupt_phrase()`  [INFERRED]
  SIDEKICK_PROTOCOL.md → src/service/interrupt_service.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Remote access path: Firebase frontend to Cloudflare Tunnel to tower API** — docs_hosting_firebase_hosting, docs_hosting_cloudflare_tunnel, docs_hosting_tower_api [EXTRACTED 0.95]
- **Mac agent core design principles** — mac_agent_readme_dial_out, mac_agent_readme_sessions_as_threads, mac_agent_readme_git_worktree [EXTRACTED 1.00]
- **Persisted-action safety rules across foreground and background agents** — prompting_nova_persona_prompt_confirm_persisted_actions, prompting_nova_persona_prompt_clarify_before_executing, prompting_background_agent_prompt_no_outward_actions [INFERRED 0.85]

## Communities (229 total, 97 thin omitted)

### Community 0 - "Tool"
Cohesion: 0.15
Nodes (6): main(), main(), main(), main(), ToolDao, Tool

### Community 1 - "nova_controller.py"
Cohesion: 0.05
Nodes (33): audio_file_bytes(), is_raw_pcm(), _pcm_params(), suffix_for_mime(), transcribe_serialized(), _canonical_wake_text(), chat_stream(), event_source() (+25 more)

### Community 2 - "SimpleFinancesService"
Cohesion: 0.11
Nodes (6): SimplApiError, SimplConfigurationError, SimpleFinancesService, response(), SimpleFinancesServiceTest, SimplFinancesToolRegistrationTest

### Community 3 - "text"
Cohesion: 0.19
Nodes (4): forward(), PathTokenRouteTests, SenderGateTests, text()

### Community 5 - "OpenAILoopTests"
Cohesion: 0.16
Nodes (7): FakeClient, FakeFunctionCall, FakeResponse, FakeResponsesAPI, FakeTool, FakeToolService, OpenAILoopTests

### Community 6 - "ServerEvent"
Cohesion: 0.06
Nodes (26): ServerEvent, audioStreamChunk, audioStreamEnd, audioStreamStart, captureRequest, chunkReceived, done, error (+18 more)

### Community 7 - "AgentLoopImageTests"
Cohesion: 0.23
Nodes (4): AgentLoopImageTests, FakeMessage, FakeTextBlock, FakeToolUseBlock

### Community 8 - "test_background_agent.py"
Cohesion: 0.05
Nodes (16): BackgroundAgentLimitTests, never_finishes(), BackgroundAgentTests, fake_get_response(), FakeConversationService, FakeMessage, FakeProjectDao, FakeTextBlock (+8 more)

### Community 10 - "make_update"
Cohesion: 0.06
Nodes (20): describe_twilio_error(), is_permanent_twilio_error(), at(), BadgeOnlyTests, build_service(), CallDeliveryTests, EmailDeliveryTests, FakeUpdateService (+12 more)

### Community 11 - "ClaudeService"
Cohesion: 0.10
Nodes (4): _env_flag(), ClaudeService, GenerationKwargsTests, ClaudeServiceMcpKwargsTests

### Community 12 - "GithubService"
Cohesion: 0.15
Nodes (4): GithubService, GithubServiceError, _FakeResponse, GithubServiceTests

### Community 13 - "build_service"
Cohesion: 0.05
Nodes (10): build_service(), CreateUpdateTests, FakeConversationDao, FakeProjectDao, FakeUpdateDao, make_update(), MultiChannelReportTypeTests, NotificationQueueFieldsTests (+2 more)

### Community 14 - "Nova system prompt (persona)"
Cohesion: 0.07
Nodes (28): Hosting Nova off the home network, Backend environment variables, Cloudflare Tunnel (nova-tower, cloudflared), Firebase Hosting frontend (nova-voice-nd.web.app), Infobip SMS integration (/sms/inbound), Failed-login lockout policy, Mac coding agent (/ws/coding), MCP OAuth callback (+20 more)

### Community 15 - "SidekickController"
Cohesion: 0.11
Nodes (12): .currentConversationId, Cancellable, ConversationIdStore, EarconPlaying, GlassesCamera, MainScheduler, NovaSocketing, Scheduling (+4 more)

### Community 16 - "agent_loop.py"
Cohesion: 0.10
Nodes (5): MessageDao, _memory_block_budget_seconds(), Message, MessageRole, ConversationService

### Community 17 - "Harness"
Cohesion: 0.08
Nodes (15): LevelSmoother, Snapshot, State, calibrating, cooldown, idle, onset, speaking (+7 more)

### Community 18 - "CodingService"
Cohesion: 0.04
Nodes (9): CodingSessionDao, CodingEvent, CodingSession, CodingService, AgentBindingTests, FakeLink, MacShellTests, StartReportTypeTests (+1 more)

### Community 19 - "ScheduledTaskService"
Cohesion: 0.09
Nodes (5): ScheduledTaskDao, ScheduledTask, TaskStatus, ScheduledTaskService, CurrentTimeTests

### Community 20 - "_most_recent_local_midnight_utc"
Cohesion: 0.13
Nodes (3): _most_recent_local_midnight_utc(), IsPastRolloverTests, MostRecentLocalMidnightUtcTests

### Community 22 - "time"
Cohesion: 0.07
Nodes (23): fetch(), main(), sha256(), _remove(), transcribe_utterance(), _all(), await_ready(), check() (+15 more)

### Community 23 - "test_memory_chunk_service.py"
Cohesion: 0.07
Nodes (13): build_service(), FakeClaudeResponse, FakeClaudeService, FakeConversationService, FakeEmbeddingService, FakeMemoryChunkDao, FakeTextBlock, FetchMemoryTests (+5 more)

### Community 24 - "meeting_controller.py"
Cohesion: 0.10
Nodes (12): transcribe_segments_serialized(), delete_meeting(), get_active_meeting(), get_meeting(), get_meeting_segments(), list_meetings(), _meeting_error(), regenerate_notes() (+4 more)

### Community 25 - "CursorService"
Cohesion: 0.17
Nodes (4): CursorService, CursorServiceError, CursorServiceTests, _FakeResponse

### Community 26 - "MeetingService"
Cohesion: 0.04
Nodes (8): MeetingChunkDao, MeetingDao, MeetingNotesDao, Meeting, MeetingChunk, MeetingNotes, MeetingError, MeetingService

### Community 27 - "FileOperationTests"
Cohesion: 0.09
Nodes (3): EditTests, FileOperationTests, PathContainmentTests

### Community 28 - "AppModel"
Cohesion: 0.13
Nodes (4): AppModel, .baseURL, .serverURLString, .body

### Community 29 - "UpdateDeliveryService"
Cohesion: 0.12
Nodes (3): EmailService, _env_int(), UpdateDeliveryService

### Community 30 - "ConversationController"
Cohesion: 0.10
Nodes (7): Capture, ConversationController, .idleMessage, .isEnabled, .isWorking, .wakeWatching, Once

### Community 31 - "Keys"
Cohesion: 0.08
Nodes (23): Keys, assistantText, bytes, chunkBase64, client, code, conversationId, count (+15 more)

### Community 32 - "deploy_main.py"
Cohesion: 0.07
Nodes (26): build_logger(), check_health_once(), current_commit(), DeployConfig, DeployError, DeployRunner, _ensure_single_healthy_api(), find_all_pids_on_port() (+18 more)

### Community 35 - "auth_service.py"
Cohesion: 0.12
Nodes (9): _client_ip(), current_session(), list_sessions(), login(), logout(), AuthNotConfigured, BadCredentials, LockedOut (+1 more)

### Community 36 - "SessionManager"
Cohesion: 0.07
Nodes (12): Config, load_env_file(), Link, _configure_logging(), main(), _run(), _task(), _as_int() (+4 more)

### Community 37 - "_runner"
Cohesion: 0.12
Nodes (5): DryRunTests, LeftoverSweepTests, RollbackPathTests, _runner(), SweepHandsOffStaleAncestorsTests

### Community 38 - "_silent_logger"
Cohesion: 0.12
Nodes (4): EnsureSingleHealthyApiTests, HelperModeCliTests, RunStaleAncestorHelperTests, _silent_logger()

### Community 39 - "json"
Cohesion: 0.10
Nodes (21): _all(), await_ready(), check(), classify(), _entry(), kill_tree(), _log_paths(), pid_alive() (+13 more)

### Community 40 - "DATGlassesCamera"
Cohesion: 0.07
Nodes (15): CameraError, .errorDescription, failed, glassesAudioNotUp, noCamera, notReady, timeout, DATGlassesCamera (+7 more)

### Community 44 - "Responsibility"
Cohesion: 0.17
Nodes (4): Responsibility, at(), CheckForResponsibilitiesTests, DueTests

### Community 45 - "McpOAuthService"
Cohesion: 0.22
Nodes (4): _b64url(), McpOAuthService, _origin(), _path()

### Community 46 - "make_update"
Cohesion: 0.16
Nodes (5): ConversationResolutionTests, make_update(), OpeningPromptTests, TwiMLTests, form()

### Community 47 - "build_service"
Cohesion: 0.14
Nodes (5): build_service(), FakeProjectDao, RetrievalTests, StartMeetingTests, StopMeetingTests

### Community 48 - "asyncio"
Cohesion: 0.04
Nodes (35): logout_all(), adopt_claude_thread(), _authorized(), coding_socket(), coding_status(), get_coding_session(), list_claude_threads(), list_coding_sessions() (+27 more)

### Community 49 - "call_controller.py"
Cohesion: 0.08
Nodes (16): answer_call(), call_status(), _escape(), mint_relay_token(), _opening_prompt(), relay_socket(), start_turn(), run_after_previous() (+8 more)

### Community 51 - "AgentLoop"
Cohesion: 0.05
Nodes (21): AgentLoop, ToolService, ConversationLoopLimitTests, CountingService, FakeConversationService, FakeToolDao, PrefetchedConversationTests, GlassesCannotRecordMeetingsTests (+13 more)

### Community 52 - "TurnTimer"
Cohesion: 0.10
Nodes (8): _emit(), TurnTimer, _drain(), _FakeMessage, _FakeStream, _FakeUsage, TurnStreamUsageMarkTests, TurnTimerTests

### Community 53 - "build_app"
Cohesion: 0.22
Nodes (3): build_app(), stream(), fake_stream()

### Community 54 - "AuthService"
Cohesion: 0.11
Nodes (3): AuthService, _hash_token(), _now()

### Community 55 - "SpeakOnCompletionTests"
Cohesion: 0.15
Nodes (4): no_tts(), SpeakOnCompletionTests, never_finishes(), scenario()

### Community 56 - "build_service"
Cohesion: 0.07
Nodes (11): build_service(), CreateTests, FakeProjectDao, FakeTaskDao, FakeUpdateService, ListAndCancelTests, pending(), RecoverStuckTests (+3 more)

### Community 57 - "FakeMessage"
Cohesion: 0.13
Nodes (13): fake_stream(), FakeMessage, FakeTextBlock, fake_stream(), fake_stream(), fake_stream(), fake_stream(), StatusTextTests (+5 more)

### Community 58 - "FakePersonaDao"
Cohesion: 0.13
Nodes (7): build_service(), CachingTests, FakePersonaDao, LoadingTests, seed_row(), ToolFacingWrapperTests, VersioningAndRollbackTests

### Community 59 - "ConversationLoopStreamTests"
Cohesion: 0.14
Nodes (4): ConversationLoopStreamTests, fake_stream(), fake_stream(), EventStreamTests

### Community 60 - "sms_controller.py"
Cohesion: 0.11
Nodes (9): _authorize(), inbound_sms(), inbound_sms_with_path_token(), _is_stale(), _receive(), resolve_sms_conversation(), _run_sms_turn(), ConversationClosedError (+1 more)

### Community 61 - "SpeechPlayer"
Cohesion: 0.07
Nodes (7): MP3StreamDecoder, PlaybackWatchdog, SpeechPlayer, .isBusy, .now, Stream, PlaybackWatchdogTests

### Community 62 - "EndpointDecisionTests"
Cohesion: 0.07
Nodes (10): caption_endpoint_decision(), _caption_floor(), endpoint_decision(), _endpoint_scale(), EndpointDecision, _ms(), _score_transcript(), silence_budget_ms() (+2 more)

### Community 63 - ".look"
Cohesion: 0.16
Nodes (11): Vision: "Hey Nova, what do you see?", Client → server, Connecting, Deviations from the brief and additions, Interjections, Prompt and tools, Server behaviour, Server → client (+3 more)

### Community 64 - "FakeCamera"
Cohesion: 0.22
Nodes (4): FakeCamera, FakeVision, settle(), VisionControllerTests

### Community 65 - "ConversationControllerTests"
Cohesion: 0.05
Nodes (14): PCMFormat, PreRollBuffer, .count, AudioFramingTests, ConversationControllerTests, ConversationControllerTests.Rig, FakePlayer, .isBusy (+6 more)

### Community 68 - "ClientEvent"
Cohesion: 0.07
Nodes (25): AudioRole, final, progress, status, wake, CapturePurpose, sentry, turn (+17 more)

### Community 69 - "NovaGlasses"
Cohesion: 0.23
Nodes (3): AudioSessionPolicyTests, NovaGlasses, XCTest

### Community 70 - "Conversation"
Cohesion: 0.10
Nodes (4): ConversationDao, Conversation, FakeConversationService, ThreadResolutionTests

### Community 71 - "test_vision.py"
Cohesion: 0.04
Nodes (18): AuthGate, bearer_token(), _header(), is_exempt(), has_be_quiet_phrase(), _normalize(), ToolExecutionError, ImageStore (+10 more)

### Community 72 - "McpServer"
Cohesion: 0.20
Nodes (3): McpServer, _now(), _parse_expiry()

### Community 74 - "TwilioService"
Cohesion: 0.07
Nodes (12): backend_url(), close_current_conversation(), fetch_conversation_info(), fetch_health(), fetch_projects(), fetch_tools(), stream_reply(), main() (+4 more)

### Community 76 - "._conversation_turn"
Cohesion: 0.04
Nodes (6): PromptSourceEnum, persist(), _PassHold, strip_expects_reply(), _strip_expects_reply_events(), GlassesPromptSourceTests

### Community 77 - "run_migrations.py"
Cohesion: 0.16
Nodes (4): main(), migration_files(), _jsonable(), SQLService

### Community 79 - "parse_gate_reply"
Cohesion: 0.22
Nodes (3): parse_gate_reply(), SidekickGate, GateReplyTests

### Community 80 - "is_nova_interrupt_phrase"
Cohesion: 0.15
Nodes (4): is_nova_interrupt_phrase(), _normalize_tokens(), NegativeMatchTests, PositiveMatchTests

### Community 81 - "fake_stream"
Cohesion: 0.10
Nodes (6): fake_stream(), FailureHistoryAndRetryTests, fake_stream(), fake_stream(), FailureSpeechTests, _FakeBadRequestError

### Community 82 - "LiveScreenTests"
Cohesion: 0.19
Nodes (3): LiveScreenTests, ScriptedTurnStream, get_final_message()

### Community 83 - "FakeMcpServerDao"
Cohesion: 0.17
Nodes (3): build_service(), FakeMcpServerDao, McpServerServiceTests

### Community 86 - "SettingsService"
Cohesion: 0.11
Nodes (3): SettingsService, ModelListTests, _ResetsSharedState

### Community 87 - "Person"
Cohesion: 0.11
Nodes (3): PersonDao, Person, FakePersonDao

### Community 88 - "bip_service.py"
Cohesion: 0.16
Nodes (4): BipConfigurationError, BipRequestError, _describe_response_error(), is_permanent_bip_error()

### Community 89 - "test_responsibility_service.py"
Cohesion: 0.11
Nodes (5): build_service(), FakeProjectDao, FakeResponsibilityDao, FakeUpdateService, WindowTests

### Community 91 - "test_deploy_main.py"
Cohesion: 0.12
Nodes (4): FailingTestsAbortTests, HappyPathTests, SpawnStaleAncestorHelperTests, WaitForPidExitTests

### Community 92 - "test_memory_injection.py"
Cohesion: 0.07
Nodes (14): MemoryChunkDao, MemoryChunk, MemoryMatch, build_memory_service(), FakeConversationService, FakeEmbeddingService, FakeMemoryChunkDao, FakeMessage (+6 more)

### Community 93 - "meeting_service.py"
Cohesion: 0.06
Nodes (9): ProjectDao, CodingStatus, MeetingStatus, Project, ProjectService, CodeServiceTestCase, FakeConversationDao, FakeProjectDao (+1 more)

### Community 94 - "ASRService"
Cohesion: 0.11
Nodes (3): ASRService, TranscriptSegment, NovaService

### Community 95 - "main.py"
Cohesion: 0.11
Nodes (7): _allowed_origins(), health(), lifespan(), root(), _broadcast(), face_socket(), SidekickService

### Community 96 - "UpdateService"
Cohesion: 0.05
Nodes (9): UpdateDao, DeliveryStatus, encode_report_types(), normalize_report_types(), ReportType, Update, UpdateService, EscapingTests (+1 more)

### Community 97 - "Mac code agent daemon"
Cohesion: 0.16
Nodes (14): Nova code agent (Mac) README, Anthropic API key stripping, Mac dials out design, Per-session git worktree, Known limits (awake Mac, bounded replay, cache cost), launchd install and menu app, Mac code agent daemon, NOVA_CODE_TOKEN shared secret (+6 more)

### Community 98 - "test_spoken_reply.py"
Cohesion: 0.16
Nodes (6): _comparable(), is_repeat(), _plain_text(), strip_speak_tags(), IsRepeatTests, StripSpeakTagsTests

### Community 100 - "recording_meeting"
Cohesion: 0.18
Nodes (5): CommitSegmentsTests, DeleteMeetingTests, recording_meeting(), RecoveryTests, UpdateMeetingTests

### Community 101 - "._run_begin"
Cohesion: 0.23
Nodes (6): BeginFlowTests, fake_get(), fake_post(), fake_post(), fake_post(), FakeResponse

### Community 105 - "asr_service.py"
Cohesion: 0.20
Nodes (8): main(), _hotwords(), _load_parakeet(), missing_cuda_libraries(), _nvidia_wheel_dll_dirs(), _platform_default_provider(), _resolve_whisper_device(), _setup_cuda_libraries()

### Community 106 - "test_sms.py"
Cohesion: 0.26
Nodes (4): _handle_inbound(), normalize_phone_number(), SmsRecipientError, NormalizationTests

### Community 108 - "ElevenLabsService"
Cohesion: 0.23
Nodes (3): _describe_failure(), ElevenLabsService, ElevenLabsRequestTests

### Community 110 - ".deploy_main"
Cohesion: 0.15
Nodes (3): HealthTimeoutTests, StopPidTreeKillTests, DeployMainTests

### Community 111 - "FakeDao"
Cohesion: 0.18
Nodes (4): CompleteAndRefreshTests, ConnectorFilteringTests, FakeDao, oauth_server()

### Community 112 - ".run_turn"
Cohesion: 0.10
Nodes (8): MemoryInjectionTests, boom(), notification(), NotificationCapTests, NotificationCrossMediumTests, NotificationRecencyTests, NotificationScopingTests, PendingNotificationsInjectionTests

### Community 113 - "protocol.py"
Cohesion: 0.39
Nodes (3): _artifact_for(), encode(), _truncate()

### Community 114 - "HomeView"
Cohesion: 0.09
Nodes (16): NovaGlassesApp, .body, RootView, .body, AudioLogView, HomeView, .cameraText, .connectionText (+8 more)

### Community 115 - "asr-bench.py"
Cohesion: 0.36
Nodes (4): cut_clips(), default_audio(), load(), main()

### Community 116 - "test_conversation_loop.py"
Cohesion: 0.07
Nodes (8): _maybe_print_prompt(), TurnStream, PromptSourceTests, SentenceChunkTests, TurnStreamTests, __iter__(), get_final_message(), get_final_message()

### Community 118 - "APIClient"
Cohesion: 0.16
Nodes (7): APIClient, APIError, badResponse, .errorDescription, server, unauthorized, Person

### Community 119 - "Foundation"
Cohesion: 0.09
Nodes (11): AudioToolbox, AVFoundation, Foundation, ImageIO, AudioSessionPolicy, MWDATCamera, MWDATCore, Observation (+3 more)

### Community 120 - "Earcon"
Cohesion: 0.11
Nodes (15): Earcons, Note, Earcon, cancel, done, error, shutter, sidekickCue (+7 more)

### Community 122 - "AuthStore"
Cohesion: 0.24
Nodes (3): AuthStore, .baseQuery, Security

### Community 125 - "worker.py"
Cohesion: 0.16
Nodes (10): BuildJobsTests, build_jobs(), _recover_stuck_tasks(), _run_check_for_responsibilities(), _run_check_for_stale_conversations(), _run_deliver_pending_updates(), _run_process_conversations(), _run_scheduled_tasks() (+2 more)

### Community 128 - "CheckForStaleConversationsTests"
Cohesion: 0.24
Nodes (3): build_service(), CheckForStaleConversationsTests, FakeConversationDao

### Community 130 - "GateTestCase"
Cohesion: 0.13
Nodes (4): GateTestCase, WebSocketGateTests, AuthServiceTestCase, LoginTests

### Community 135 - "history_compaction.py"
Cohesion: 0.20
Nodes (15): _block_chars(), cap_messages(), clear_old_tool_results(), _clearable_blocks(), compact_history(), _env_int(), _is_plain_user_turn(), _history() (+7 more)

### Community 137 - "SidekickConnection"
Cohesion: 0.15
Nodes (3): Utterances, sidekick_socket(), SidekickConnection

### Community 139 - "AudioRouteManager"
Cohesion: 0.22
Nodes (3): AudioRouteManager, Route, .summary

### Community 141 - "VoiceMode"
Cohesion: 0.14
Nodes (11): VoiceMode, conversation, sentry, VoiceModeStore, Build and test (CLI), Code map, How it behaves, Install on your iPhone (+3 more)

### Community 148 - "FakeSendWebSocket"
Cohesion: 0.14
Nodes (5): FakeSendWebSocket, InterruptAndCancelWiringTests, scenario(), scenario(), scenario()

### Community 153 - "VisionService"
Cohesion: 0.05
Nodes (15): capture_failed(), read_jpeg_body(), upload_image(), Identification, CaptureFailed, InvalidImage, is_image_block(), prepare() (+7 more)

### Community 154 - "test_asr_filters.py"
Cohesion: 0.26
Nodes (4): drop_hallucination(), DropHallucinationTests, _segment(), WhisperSegmentFilterTests

### Community 155 - "MemoryChunkService"
Cohesion: 0.07
Nodes (4): EmbeddingService, MemoryChunkService, ParseChunksTests, RetrievableQueryTests

### Community 156 - "replay_request.py"
Cohesion: 0.20
Nodes (5): main(), one_call(), main(), one_call(), variants()

### Community 157 - "host_environment_prompt.py"
Cohesion: 0.31
Nodes (3): host_environment_prompt(), _host_kind(), _machine_line()

### Community 158 - "PassSentinelTests"
Cohesion: 0.10
Nodes (9): is_sidekick_pass(), FakeMessage, FakeTextBlock, FakeToolUseBlock, FakeUpdateService, _live(), LookToolExclusionTests, fake_stream() (+1 more)

### Community 159 - "TTSService"
Cohesion: 0.12
Nodes (7): _build_provider(), _ChainedProvider, OpenAITTS, TTSService, _cartesia(), _eleven_labs(), _mock_chain()

### Community 165 - "settings_controller.py"
Cohesion: 0.11
Nodes (6): get_all_settings(), get_available_models(), get_claude_credits(), ModelSwitchRequest, set_model(), ClaudeCreditsService

### Community 170 - "worktree.py"
Cohesion: 0.22
Nodes (7): create(), _git(), remove(), resolve_repo(), slugify(), Workspace, WorktreeError

### Community 172 - "FakeHttp"
Cohesion: 0.20
Nodes (5): build_service(), FakeHttp, InfobipRequestTests, RecipientAllowlistTests, SendSmsTests

### Community 173 - "CommandLineService"
Cohesion: 0.07
Nodes (3): CommandLineService, BackgroundTests, ForegroundTests

### Community 174 - "ToolServiceTests"
Cohesion: 0.19
Nodes (3): DemoService, FakeToolDao, ToolServiceTests

### Community 175 - "meeting_socket"
Cohesion: 0.48
Nodes (6): meeting_socket(), capture_loop(), flush_tail(), send(), _transcribe_tail(), _resolve_meeting_id()

### Community 179 - "SentryModeTests"
Cohesion: 0.09
Nodes (3): SentryModeTests, WakePhraseAloneTests, WakeStraightToListeningTests

### Community 181 - "AddPersonView"
Cohesion: 0.11
Nodes (8): .api, ImagePrep, VisionClient, AddPersonView, .body, FacesView, .body, PhotosUI

### Community 182 - "PersonaPrompt"
Cohesion: 0.13
Nodes (3): PromptEnums, PersonaPromptDao, PersonaPrompt

### Community 183 - ".setUp"
Cohesion: 0.13
Nodes (3): fake_transcribe(), FakeGate, FakeSidekickLoop

### Community 186 - "os"
Cohesion: 0.06
Nodes (14): _flag(), _contained(), make_guard(), can_use_tool(), _is_prose(), _build_file_logger(), _default_log_path(), mark() (+6 more)

### Community 191 - "MacSessionLifecycleTests"
Cohesion: 0.10
Nodes (3): MacConcurrentSessionTests, MacSessionLifecycleTests, sink()

### Community 195 - "String"
Cohesion: 0.11
Nodes (17): Phase, idle, listening, off, sentryBlocked, speaking, thinking, PhotoSlot (+9 more)

### Community 196 - "InterruptedToolCallTests"
Cohesion: 0.20
Nodes (4): FakeToolUseBlock, InterruptedToolCallTests, fake_stream(), _call()

### Community 205 - "FaceService"
Cohesion: 0.07
Nodes (17): add_sample(), create_person(), delete_person(), _enroll(), DuplicatePerson, EnrollmentError, FaceModelsMissing, FaceService (+9 more)

### Community 207 - "_FakeTable"
Cohesion: 0.13
Nodes (4): CheckForStaleConversationsLoopTests, _FakeResponse, _FakeSupabaseClient, _FakeTable

### Community 208 - "clamp_spoken"
Cohesion: 0.23
Nodes (5): deliver(), mark_first_speech(), _clamp(), clamp_spoken(), ClampSpokenTests

### Community 213 - "MeetingSegment"
Cohesion: 0.13
Nodes (6): MeetingSegment, ChunkingTests, FinalizeTests, NotesTests, NotesUseNoToolsTests, TranscriptTests

### Community 231 - "Entry"
Cohesion: 0.36
Nodes (3): AudioLog, Entry, .body

## Ambiguous Edges - Review These
- `TTS conversion enhancer prompt (empty)` → `Voice mode tone guidelines`  [AMBIGUOUS]
  prompting/tts_conversion_enhancer_prompt.txt · relation: conceptually_related_to

## Knowledge Gaps
- **165 isolated node(s):** `UserNotifications`, `.serverURLString`, `.summary`, `AudioToolbox`, `.count` (+160 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1765 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **97 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `TTS conversion enhancer prompt (empty)` and `Voice mode tone guidelines`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `NovaGlasses` connect `VoiceMode` to `AmbientForwardingTests`, `.look`?**
  _High betweenness centrality (0.312) - this node is a cross-community bridge._
- **Are the 45 inferred relationships involving `AgentLoop` (e.g. with `Server behaviour` and `PromptEnums`) actually correct?**
  _`AgentLoop` has 45 INFERRED edges - model-reasoned connections that need verification._
- **What connects `UserNotifications`, `.serverURLString`, `.summary` to the rest of the system?**
  _165 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Tool` be split into smaller, more focused modules?**
  _Cohesion score 0.14616755793226383 - nodes in this community are weakly interconnected._
- **Why does `Vision: "Hey Nova, what do you see?"` connect `.look` to `VoiceMode`?**
  _High betweenness centrality (0.312) - this node is a cross-community bridge._
- **Are the 22 inferred relationships involving `Conversation` (e.g. with `_is_stale()` and `ConversationDao`) actually correct?**
  _`Conversation` has 22 INFERRED edges - model-reasoned connections that need verification._