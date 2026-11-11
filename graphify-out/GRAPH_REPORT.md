# Graph Report - nova-backend  (2026-11-11)

## Corpus Check
- 232 files · ~201,136 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: (none) 3, .mdc 1, .pbxproj 1)

## Summary
- 4999 nodes · 11751 edges · 232 communities (123 shown, 109 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 1264 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `795432c0`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Tool
- _receive
- SimpleFinancesService
- text
- TranscribeSocketTests
- test_openai_loop.py
- Rig
- AgentLoopImageTests
- .run_agent
- ._env
- make_update
- ClaudeService
- GithubService
- build_service
- Nova system prompt (persona)
- HomeView
- Harness
- CodingService
- ScheduledTaskService
- _most_recent_local_midnight_utc
- processes.py
- json
- test_memory_chunk_service.py
- meeting_controller.py
- CursorService
- MeetingService
- FileOperationTests
- CodingSession
- Update
- ConversationController
- ElevenLabsService
- ProviderSelectionTests
- NovaSession
- LiveReply
- test_auth_service.py
- SessionManager
- __main__.py
- CodeService
- post
- DATGlassesCamera
- Sendable
- build_service
- ResponsibilityService
- Responsibility
- McpOAuthService
- make_update
- build_service
- asr_service.py
- PromptSourceEnum
- McpServerService
- requests
- TurnTimer
- test_auth_gate.py
- AuthService
- Project
- CreateTests
- FakeMessage
- FakePersonaDao
- ConversationLoopStreamTests
- ReplyTests
- SpeechPlayer
- EndpointDecisionTests
- VisionService
- FakeCamera
- ConversationControllerTests
- ._artifact_for_tool
- test_spoken_reply.py
- ClientEvent
- MacShellTests
- Conversation
- nova_controller.py
- McpServer
- PersonaService
- TwilioService
- HttpGateTests
- AgentLoop
- faces_controller.py
- PreRollBuffer
- parse_gate_reply
- AuthStore
- fake_stream
- LiveScreenTests
- FakeMcpServerDao
- FakeMeetingDao
- CrudTests
- ModelListTests
- Person
- test_sms.py
- ServerEvent
- StreamedSpeechTests
- test_coding_service.py
- build_memory_service
- test_responsibility_service.py
- ASRService
- AsrLock
- asr-bench.py
- Mac code agent daemon
- FakeTaskDao
- ServiceMethodToolConfig
- set_model
- ._run_begin
- email_service.py
- NovaSocket
- Keys
- FaceService
- MemoryChunk
- HostEnvironmentPromptTests
- VoiceMode
- .repair_tool_pairing
- test_asr_filters.py
- FakeDao
- MemoryInjectionTests
- sessions.py
- AppModel
- meeting_service.py
- speech_summary
- match
- APIClient
- Foundation
- Earcon
- SidekickSocketTests
- PromptSourceTests
- EndSessionTests
- SidekickSession
- worker.py
- SidekickController
- GithubServiceTests
- os
- ._to_dict
- FakeDao
- ClassificationTests
- .transcript
- CaptureEngine
- history_compaction.py
- pathlib
- SidekickConnection
- WorkingTreeTests
- AudioRouteManager
- .isOnlyWakePhrase
- run_migrations.py
- SpokenProse
- TTSService
- test_background_agent.py
- RelayTokenTests
- SpeechWakeDetector
- AuthenticateTests
- clamp_spoken
- PerformTests
- SpokenTrackTests
- .iter_sentence_chunks
- GoodbyeTimingTests
- FaceServiceTests
- .completed
- NovaGlasses
- fetch_face_models.py
- FallbackChainTests
- PassSentinelTests
- Rig
- CLAUDE.md
- asyncio
- install.sh
- uninstall.sh
- ClaudeCreditsService
- nova-backend
- worktree.py
- SettingsService
- FakeHttp
- CommandLineService
- DemoService
- CooldownTests
- BipService
- prepare
- .test_a_live_turn_reads_deltas_then_exposes_the_message
- .add
- .__init__
- AddPersonView
- PersonaPrompt
- .setUp
- answer_call
- update_controller.py
- replay_request.py
- .wantsToSee
- .identify
- dict
- MacSessionLifecycleTests
- XCTestCase
- meeting_socket
- SentryModeTests
- CreateScheduleRequirementTests
- InterruptedToolCallTests
- _said
- FakePersonDao
- ThinkingPulseTests
- GuardrailTests
- SidekickService
- StatusTextTests
- test_settings_service.py
- Link
- FakeSocket
- AgentLink
- _FakeTable
- shell.py
- MirrorTests
- FinishedSessionTowerTests
- protocol.py
- _ResetsSharedCache
- .split_sms_body
- kill_tree
- .allowed_sms_senders
- face_controller.py
- FakeConversationService
- ToolUseStarted
- ConnectorFilteringTests
- WebSocketGateTests
- CodingStatus
- TranscribeUtteranceTests
- make_request
- FakeResponse
- classify
- _describe_failure

## God Nodes (most connected - your core abstractions)
1. `AgentLoop` - 121 edges
2. `Conversation` - 89 edges
3. `ConversationController` - 83 edges
4. `ToolService` - 66 edges
5. `build_service()` - 57 edges
6. `MeetingService` - 52 edges
7. `CodingService` - 49 edges
8. `Responsibility` - 47 edges
9. `Tool` - 46 edges
10. `ServerEvent` - 44 edges

## Surprising Connections (you probably didn't know these)
- `Server behaviour` --references--> `audio_file_bytes()`  [INFERRED]
  SIDEKICK_PROTOCOL.md → src/controller/audio_ws.py
- `Server → client` --references--> `stream_tts_audio()`  [INFERRED]
  SIDEKICK_PROTOCOL.md → src/controller/nova_controller.py
- `Server behaviour` --references--> `AgentLoop`  [INFERRED]
  SIDEKICK_PROTOCOL.md → src/harness/agent_loop.py
- `Server behaviour` --references--> `ClaudeService`  [INFERRED]
  SIDEKICK_PROTOCOL.md → src/service/claude_service.py
- `Interjections` --references--> `text()`  [INFERRED]
  SIDEKICK_PROTOCOL.md → tests/test_sms_controller.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Remote access path: Firebase frontend to Cloudflare Tunnel to tower API** — docs_hosting_firebase_hosting, docs_hosting_cloudflare_tunnel, docs_hosting_tower_api [EXTRACTED 0.95]
- **Mac agent core design principles** — mac_agent_readme_dial_out, mac_agent_readme_sessions_as_threads, mac_agent_readme_git_worktree [EXTRACTED 1.00]
- **Persisted-action safety rules across foreground and background agents** — prompting_nova_persona_prompt_confirm_persisted_actions, prompting_nova_persona_prompt_clarify_before_executing, prompting_background_agent_prompt_no_outward_actions [INFERRED 0.85]

## Communities (232 total, 109 thin omitted)

### Community 0 - "Tool"
Cohesion: 0.16
Nodes (4): ToolDao, Tool, FakeToolDao, ToolServiceTests

### Community 1 - "_receive"
Cohesion: 0.31
Nodes (4): _authorize(), inbound_sms(), inbound_sms_with_path_token(), _receive()

### Community 2 - "SimpleFinancesService"
Cohesion: 0.11
Nodes (6): SimplApiError, SimplConfigurationError, SimpleFinancesService, response(), SimpleFinancesServiceTest, SimplFinancesToolRegistrationTest

### Community 3 - "text"
Cohesion: 0.16
Nodes (5): AuthenticationTests, forward(), PathTokenRouteTests, SenderGateTests, text()

### Community 5 - "test_openai_loop.py"
Cohesion: 0.17
Nodes (7): FakeClient, FakeFunctionCall, FakeResponse, FakeResponsesAPI, FakeTool, FakeToolService, OpenAILoopTests

### Community 6 - "Rig"
Cohesion: 0.13
Nodes (6): FakePlayer, .isBusy, FakeWake, Item, ManualScheduler, Rig

### Community 7 - "AgentLoopImageTests"
Cohesion: 0.33
Nodes (4): AgentLoopImageTests, FakeMessage, FakeTextBlock, FakeToolUseBlock

### Community 8 - ".run_agent"
Cohesion: 0.11
Nodes (3): BackgroundAgentTests, ReportTypeTests, ResponsibilityRunToolRestrictionTests

### Community 10 - "make_update"
Cohesion: 0.07
Nodes (18): describe_twilio_error(), is_permanent_twilio_error(), at(), BadgeOnlyTests, build_service(), CallDeliveryTests, EmailDeliveryTests, FakeUpdateService (+10 more)

### Community 11 - "ClaudeService"
Cohesion: 0.09
Nodes (5): _env_flag(), ClaudeService, _maybe_print_prompt(), GenerationKwargsTests, ClaudeServiceMcpKwargsTests

### Community 13 - "build_service"
Cohesion: 0.08
Nodes (8): build_service(), CreateUpdateTests, FakeConversationDao, FakeProjectDao, FakeUpdateDao, make_update(), ReportTypeTests, ViewingTests

### Community 14 - "Nova system prompt (persona)"
Cohesion: 0.07
Nodes (28): Hosting Nova off the home network, Backend environment variables, Cloudflare Tunnel (nova-tower, cloudflared), Firebase Hosting frontend (nova-voice-nd.web.app), Infobip SMS integration (/sms/inbound), Failed-login lockout policy, Mac coding agent (/ws/coding), MCP OAuth callback (+20 more)

### Community 15 - "HomeView"
Cohesion: 0.08
Nodes (16): ImageIO, NovaGlassesApp, .body, RootView, ImagePrep, AudioLogView, HomeView, .cameraText (+8 more)

### Community 17 - "Harness"
Cohesion: 0.08
Nodes (19): LevelSmoother, Snapshot, State, calibrating, cooldown, idle, onset, speaking (+11 more)

### Community 19 - "ScheduledTaskService"
Cohesion: 0.09
Nodes (4): ScheduledTask, TaskStatus, ScheduledTaskService, CurrentTimeTests

### Community 20 - "_most_recent_local_midnight_utc"
Cohesion: 0.07
Nodes (7): _most_recent_local_midnight_utc(), IsIdleTests, IsPastRolloverTests, build_service(), CheckForStaleConversationsTests, FakeConversationDao, MostRecentLocalMidnightUtcTests

### Community 21 - "processes.py"
Cohesion: 0.16
Nodes (16): _all(), await_ready(), check(), _entry(), kill_tree(), _log_paths(), pid_alive(), port_open() (+8 more)

### Community 22 - "json"
Cohesion: 0.13
Nodes (15): _all(), await_ready(), check(), _entry(), _log_paths(), port_open(), _prune(), read_log() (+7 more)

### Community 23 - "test_memory_chunk_service.py"
Cohesion: 0.07
Nodes (13): build_service(), FakeClaudeResponse, FakeClaudeService, FakeConversationService, FakeEmbeddingService, FakeMemoryChunkDao, FakeTextBlock, FetchMemoryTests (+5 more)

### Community 24 - "meeting_controller.py"
Cohesion: 0.11
Nodes (12): delete_meeting(), get_active_meeting(), get_meeting(), get_meeting_segments(), list_meetings(), _meeting_error(), regenerate_notes(), _resolve_meeting_id() (+4 more)

### Community 25 - "CursorService"
Cohesion: 0.17
Nodes (4): CursorService, CursorServiceError, CursorServiceTests, _FakeResponse

### Community 26 - "MeetingService"
Cohesion: 0.05
Nodes (4): MeetingDao, Meeting, MeetingError, MeetingService

### Community 27 - "FileOperationTests"
Cohesion: 0.09
Nodes (3): EditTests, FileOperationTests, PathContainmentTests

### Community 28 - "CodingSession"
Cohesion: 0.17
Nodes (3): CodingSessionDao, CodingEvent, CodingSession

### Community 29 - "Update"
Cohesion: 0.05
Nodes (10): ScheduledTaskDao, UpdateDao, DeliveryStatus, ReportType, Update, user_phone_number(), _env_int(), UpdateDeliveryService (+2 more)

### Community 30 - "ConversationController"
Cohesion: 0.10
Nodes (8): Capture, ConversationController, .idleMessage, .isEnabled, .isWorking, .wakeWatching, Once, Sentry mode

### Community 31 - "ElevenLabsService"
Cohesion: 0.21
Nodes (3): _describe_failure(), ElevenLabsService, ElevenLabsRequestTests

### Community 35 - "test_auth_service.py"
Cohesion: 0.09
Nodes (8): row_to_session(), AuthNotConfigured, BadCredentials, LockedOut, _now(), LockoutTests, LoginTests, RowConversionTests

### Community 37 - "__main__.py"
Cohesion: 0.15
Nodes (7): Config, _flag(), load_env_file(), _configure_logging(), main(), _run(), _task()

### Community 39 - "post"
Cohesion: 0.13
Nodes (13): adopt_claude_thread(), _authorized(), coding_socket(), coding_status(), get_coding_session(), list_claude_threads(), list_coding_sessions(), read_claude_thread() (+5 more)

### Community 40 - "DATGlassesCamera"
Cohesion: 0.07
Nodes (8): CameraError, .errorDescription, failed, glassesAudioNotUp, noCamera, notReady, timeout, DATGlassesCamera

### Community 41 - "Sendable"
Cohesion: 0.14
Nodes (9): Cancellable, GlassesCameraState, .canCapture, ready, registering, streaming, unavailable, unregistered (+1 more)

### Community 42 - "build_service"
Cohesion: 0.15
Nodes (8): build_service(), FakeProjectDao, FakeUpdateService, ListAndCancelTests, pending(), RecoverStuckTests, RunDueTests, RunTests

### Community 44 - "Responsibility"
Cohesion: 0.15
Nodes (5): Responsibility, at(), CheckForResponsibilitiesTests, DueTests, ReportMediumTests

### Community 45 - "McpOAuthService"
Cohesion: 0.24
Nodes (3): McpOAuthService, _origin(), _path()

### Community 46 - "make_update"
Cohesion: 0.16
Nodes (5): ConversationResolutionTests, make_update(), OpeningPromptTests, TwiMLTests, form()

### Community 47 - "build_service"
Cohesion: 0.04
Nodes (26): MeetingSegment, build_service(), ChunkingTests, CommitSegmentsTests, DeleteMeetingTests, FakeAgentLoop, FakeChunkDao, FakeClaudeService (+18 more)

### Community 48 - "asr_service.py"
Cohesion: 0.19
Nodes (8): main(), _hotwords(), _load_parakeet(), missing_cuda_libraries(), _nvidia_wheel_dll_dirs(), _platform_default_provider(), _resolve_whisper_device(), _setup_cuda_libraries()

### Community 49 - "PromptSourceEnum"
Cohesion: 0.06
Nodes (14): PromptSourceEnum, mint_relay_token(), _opening_prompt(), relay_socket(), start_turn(), run_after_previous(), _resolve_conversation_id(), _run_turn() (+6 more)

### Community 51 - "requests"
Cohesion: 0.27
Nodes (7): backend_url(), close_current_conversation(), fetch_conversation_info(), fetch_health(), fetch_projects(), fetch_tools(), stream_reply()

### Community 52 - "TurnTimer"
Cohesion: 0.10
Nodes (8): _emit(), TurnTimer, _drain(), _FakeMessage, _FakeStream, _FakeUsage, TurnStreamUsageMarkTests, TurnTimerTests

### Community 53 - "test_auth_gate.py"
Cohesion: 0.11
Nodes (7): AuthGate, bearer_token(), _header(), is_exempt(), build_app(), ExemptionTests, SidekickAuthTests

### Community 54 - "AuthService"
Cohesion: 0.11
Nodes (4): AuthService, GateTestCase, AuthServiceTestCase, ConfigurationTests

### Community 55 - "Project"
Cohesion: 0.07
Nodes (8): MessageDao, ProjectDao, Project, ProjectService, CodeServiceTestCase, FakeConversationDao, FakeProjectDao, ProjectResolutionTests

### Community 57 - "FakeMessage"
Cohesion: 0.22
Nodes (7): FakeMessage, FakeTextBlock, fake_stream(), fake_stream(), fake_stream(), ToolTurnSpeechTests, fake_stream()

### Community 58 - "FakePersonaDao"
Cohesion: 0.13
Nodes (6): build_service(), CachingTests, FakePersonaDao, LoadingTests, seed_row(), VersioningAndRollbackTests

### Community 59 - "ConversationLoopStreamTests"
Cohesion: 0.15
Nodes (4): ConversationLoopStreamTests, fake_stream(), fake_stream(), EventStreamTests

### Community 61 - "SpeechPlayer"
Cohesion: 0.07
Nodes (7): MP3StreamDecoder, PlaybackWatchdog, SpeechPlayer, .isBusy, .now, Stream, PlaybackWatchdogTests

### Community 63 - "VisionService"
Cohesion: 0.04
Nodes (21): Client → server, Connecting, Deviations from the brief and additions, Interjections, Prompt and tools, Server behaviour, Server → client, Sidekick protocol: `WS /ws/sidekick` (+13 more)

### Community 64 - "FakeCamera"
Cohesion: 0.21
Nodes (4): FakeCamera, FakeVision, settle(), VisionControllerTests

### Community 67 - "test_spoken_reply.py"
Cohesion: 0.16
Nodes (6): _comparable(), is_repeat(), _plain_text(), strip_speak_tags(), IsRepeatTests, StripSpeakTagsTests

### Community 68 - "ClientEvent"
Cohesion: 0.06
Nodes (33): Note, Phase, idle, listening, off, sentryBlocked, speaking, thinking (+25 more)

### Community 70 - "Conversation"
Cohesion: 0.04
Nodes (11): Conversation, Message, ConversationService, EmbeddingService, MemoryChunkService, FakeConversationService, ParseChunksTests, FakeConversationService (+3 more)

### Community 71 - "nova_controller.py"
Cohesion: 0.04
Nodes (41): audio_file_bytes(), is_raw_pcm(), _pcm_params(), suffix_for_mime(), transcribe_serialized(), _canonical_wake_text(), chat_stream(), event_source() (+33 more)

### Community 72 - "McpServer"
Cohesion: 0.19
Nodes (4): McpServer, _b64url(), _now(), _parse_expiry()

### Community 74 - "TwilioService"
Cohesion: 0.10
Nodes (5): main(), report(), TwilioConfigurationError, TwilioService, ConfigurationGuardTests

### Community 76 - "AgentLoop"
Cohesion: 0.03
Nodes (22): AgentLoop, persist(), _memory_block_budget_seconds(), _PassHold, strip_expects_reply(), _strip_expects_reply_events(), ToolService, CountingService (+14 more)

### Community 77 - "faces_controller.py"
Cohesion: 0.11
Nodes (11): add_sample(), create_person(), delete_person(), _enroll(), list_people(), read_jpeg_body(), upload_image(), DuplicatePerson (+3 more)

### Community 78 - "PreRollBuffer"
Cohesion: 0.19
Nodes (4): PCMFormat, PreRollBuffer, .count, AudioFramingTests

### Community 79 - "parse_gate_reply"
Cohesion: 0.18
Nodes (3): parse_gate_reply(), SidekickGate, GateReplyTests

### Community 80 - "AuthStore"
Cohesion: 0.24
Nodes (3): AuthStore, .baseQuery, Security

### Community 81 - "fake_stream"
Cohesion: 0.09
Nodes (6): fake_stream(), fake_stream(), fake_stream(), fake_stream(), FailureSpeechTests, _FakeBadRequestError

### Community 83 - "FakeMcpServerDao"
Cohesion: 0.17
Nodes (3): build_service(), FakeMcpServerDao, McpServerServiceTests

### Community 88 - "test_sms.py"
Cohesion: 0.13
Nodes (6): BipConfigurationError, BipRequestError, is_permanent_bip_error(), normalize_phone_number(), SmsRecipientError, NormalizationTests

### Community 89 - "ServerEvent"
Cohesion: 0.06
Nodes (26): ServerEvent, audioStreamChunk, audioStreamEnd, audioStreamStart, captureRequest, chunkReceived, done, error (+18 more)

### Community 90 - "StreamedSpeechTests"
Cohesion: 0.27
Nodes (3): stream(), StreamedSpeechTests, fake_stream()

### Community 92 - "build_memory_service"
Cohesion: 0.26
Nodes (5): build_memory_service(), FakeEmbeddingService, FakeMemoryChunkDao, match(), RetrieveContextTests

### Community 93 - "test_responsibility_service.py"
Cohesion: 0.11
Nodes (5): build_service(), FakeProjectDao, FakeResponsibilityDao, FakeUpdateService, WindowTests

### Community 96 - "asr-bench.py"
Cohesion: 0.36
Nodes (4): cut_clips(), default_audio(), load(), main()

### Community 97 - "Mac code agent daemon"
Cohesion: 0.16
Nodes (14): Nova code agent (Mac) README, Anthropic API key stripping, Mac dials out design, Per-session git worktree, Known limits (awake Mac, bounded replay, cache cost), launchd install and menu app, Mac code agent daemon, NOVA_CODE_TOKEN shared secret (+6 more)

### Community 100 - "set_model"
Cohesion: 0.20
Nodes (4): get_all_settings(), get_available_models(), ModelSwitchRequest, set_model()

### Community 101 - "._run_begin"
Cohesion: 0.29
Nodes (4): BeginFlowTests, fake_get(), fake_post(), FakeResponse

### Community 104 - "Keys"
Cohesion: 0.08
Nodes (24): Keys, assistantText, bytes, chunkBase64, client, code, conversationId, count (+16 more)

### Community 106 - "MemoryChunk"
Cohesion: 0.13
Nodes (3): MemoryChunkDao, MemoryChunk, MemoryMatch

### Community 108 - "VoiceMode"
Cohesion: 0.26
Nodes (4): VoiceMode, conversation, sentry, VoiceModeStore

### Community 110 - "test_asr_filters.py"
Cohesion: 0.26
Nodes (4): drop_hallucination(), DropHallucinationTests, _segment(), WhisperSegmentFilterTests

### Community 111 - "FakeDao"
Cohesion: 0.19
Nodes (5): fake_post(), CompleteAndRefreshTests, fake_post(), FakeDao, oauth_server()

### Community 113 - "sessions.py"
Cohesion: 0.15
Nodes (7): _contained(), make_guard(), can_use_tool(), _as_int(), _ms_to_iso(), health(), root()

### Community 114 - "AppModel"
Cohesion: 0.14
Nodes (6): AppModel, .serverURLString, .body, .body, LoginView, .body

### Community 115 - "meeting_service.py"
Cohesion: 0.07
Nodes (8): BaseDao, ConversationDao, MeetingChunkDao, MeetingNotesDao, ResponsibilityDao, MeetingChunk, MeetingNotes, MeetingStatus

### Community 117 - "match"
Cohesion: 0.38
Nodes (4): GalleryPerson, match(), MatchTests, unit()

### Community 118 - "APIClient"
Cohesion: 0.17
Nodes (7): APIClient, APIError, badResponse, .errorDescription, server, unauthorized, Person

### Community 119 - "Foundation"
Cohesion: 0.10
Nodes (9): AudioToolbox, AVFoundation, Foundation, AudioSessionPolicy, MWDATCamera, MWDATCore, Observation, Speech (+1 more)

### Community 120 - "Earcon"
Cohesion: 0.13
Nodes (14): Earcons, Earcon, cancel, done, error, shutter, sidekickCue, sidekickOff (+6 more)

### Community 125 - "worker.py"
Cohesion: 0.16
Nodes (10): BuildJobsTests, build_jobs(), _recover_stuck_tasks(), _run_check_for_responsibilities(), _run_check_for_stale_conversations(), _run_deliver_pending_updates(), _run_process_conversations(), _run_scheduled_tasks() (+2 more)

### Community 126 - "SidekickController"
Cohesion: 0.10
Nodes (11): ConversationIdStore, EarconPlaying, GlassesCamera, MainScheduler, NovaSocketing, Scheduling, SpeechPlaying, VisionUploading (+3 more)

### Community 128 - "os"
Cohesion: 0.05
Nodes (23): host_environment_prompt(), _host_kind(), _machine_line(), _handle_inbound(), _is_stale(), resolve_sms_conversation(), _run_sms_turn(), is_sidekick_pass() (+15 more)

### Community 135 - "history_compaction.py"
Cohesion: 0.20
Nodes (15): _block_chars(), cap_messages(), clear_old_tool_results(), _clearable_blocks(), compact_history(), _env_int(), _is_plain_user_turn(), _history() (+7 more)

### Community 136 - "pathlib"
Cohesion: 0.19
Nodes (3): main(), main(), main()

### Community 137 - "SidekickConnection"
Cohesion: 0.16
Nodes (3): Utterances, sidekick_socket(), SidekickConnection

### Community 139 - "AudioRouteManager"
Cohesion: 0.22
Nodes (3): AudioRouteManager, Route, .summary

### Community 141 - "run_migrations.py"
Cohesion: 0.19
Nodes (4): main(), migration_files(), _jsonable(), SQLService

### Community 144 - "test_background_agent.py"
Cohesion: 0.17
Nodes (9): fake_get_response(), FakeConversationService, FakeMessage, FakeProjectDao, FakeTextBlock, FakeToolDao, FakeUpdateService, fake_get_response() (+1 more)

### Community 148 - "clamp_spoken"
Cohesion: 0.23
Nodes (5): deliver(), mark_first_speech(), _clamp(), clamp_spoken(), ClampSpokenTests

### Community 154 - ".completed"
Cohesion: 0.19
Nodes (10): fake_stream(), fake_stream(), fake_stream(), fake_stream(), fake_stream(), fake_stream(), fake_stream(), FakeBlock (+2 more)

### Community 155 - "NovaGlasses"
Cohesion: 0.29
Nodes (6): Build and test (CLI), How it behaves, Install on your iPhone, NovaGlasses, On-device field checklist, Vision: "Hey Nova, what do you see?"

### Community 156 - "fetch_face_models.py"
Cohesion: 0.31
Nodes (4): fetch(), main(), sha256(), _hash_token()

### Community 158 - "PassSentinelTests"
Cohesion: 0.20
Nodes (7): FakeMessage, FakeTextBlock, FakeToolUseBlock, _live(), get_final_message(), fake_stream(), PassSentinelTests

### Community 159 - "Rig"
Cohesion: 0.18
Nodes (3): Rig, SidekickControllerTests, SidekickEventCodingTests

### Community 161 - "asyncio"
Cohesion: 0.04
Nodes (26): _allowed_origins(), lifespan(), _client_ip(), current_session(), list_sessions(), login(), logout(), logout_all() (+18 more)

### Community 170 - "worktree.py"
Cohesion: 0.22
Nodes (7): create(), _git(), remove(), resolve_repo(), slugify(), Workspace, WorktreeError

### Community 172 - "FakeHttp"
Cohesion: 0.25
Nodes (4): build_service(), FakeHttp, InfobipRequestTests, SendSmsTests

### Community 173 - "CommandLineService"
Cohesion: 0.07
Nodes (3): CommandLineService, BackgroundTests, ForegroundTests

### Community 176 - "BipService"
Cohesion: 0.17
Nodes (3): BipService, _describe_response_error(), _parse_number_list()

### Community 177 - "prepare"
Cohesion: 0.16
Nodes (6): Identification, prepare(), FakeFaceService, jpeg(), PrepareTests, VisionRoutesTests

### Community 178 - ".test_a_live_turn_reads_deltas_then_exposes_the_message"
Cohesion: 0.13
Nodes (4): TurnStreamTests, get_final_message(), __iter__(), get_final_message()

### Community 179 - ".add"
Cohesion: 0.31
Nodes (3): AudioLog, Entry, .body

### Community 180 - ".__init__"
Cohesion: 0.14
Nodes (6): _build_provider(), _ChainedProvider, OpenAITTS, _cartesia(), _eleven_labs(), _mock_chain()

### Community 181 - "AddPersonView"
Cohesion: 0.15
Nodes (7): .api, VisionClient, AddPersonView, .body, FacesView, .body, PhotosUI

### Community 182 - "PersonaPrompt"
Cohesion: 0.13
Nodes (3): PromptEnums, PersonaPromptDao, PersonaPrompt

### Community 183 - ".setUp"
Cohesion: 0.12
Nodes (4): DirectTurnCounterTests, fake_transcribe(), FakeGate, FakeSidekickLoop

### Community 184 - "answer_call"
Cohesion: 0.27
Nodes (5): answer_call(), call_status(), _escape(), _twiml(), _verified_form()

### Community 185 - "update_controller.py"
Cohesion: 0.22
Nodes (4): list_unviewed_updates(), list_updates(), mark_all_updates_viewed(), mark_update_viewed()

### Community 186 - "replay_request.py"
Cohesion: 0.20
Nodes (5): main(), one_call(), main(), one_call(), variants()

### Community 190 - "dict"
Cohesion: 0.25
Nodes (3): basic(), InboundSecretTests, RecipientAllowlistTests

### Community 192 - "XCTestCase"
Cohesion: 0.10
Nodes (7): AudioSessionPolicyTests, AmbientForwardingTests, WakePhraseAloneTests, WakeStraightToListeningTests, What is verified and what is not, NovaGlasses, XCTest

### Community 193 - "meeting_socket"
Cohesion: 0.39
Nodes (6): transcribe_segments_serialized(), meeting_socket(), capture_loop(), flush_tail(), send(), _transcribe_tail()

### Community 196 - "InterruptedToolCallTests"
Cohesion: 0.26
Nodes (3): FakeToolUseBlock, InterruptedToolCallTests, _call()

### Community 205 - "FakeSocket"
Cohesion: 0.17
Nodes (7): SocketConnectionState, connected, connecting, disconnected, unauthorized, FakeSocket, .starts

### Community 207 - "_FakeTable"
Cohesion: 0.13
Nodes (4): CheckForStaleConversationsLoopTests, _FakeResponse, _FakeSupabaseClient, _FakeTable

### Community 208 - "shell.py"
Cohesion: 0.27
Nodes (5): classify(), _clip(), _resolve_cwd(), run(), _scratch_pair()

### Community 212 - "protocol.py"
Cohesion: 0.39
Nodes (3): _artifact_for(), encode(), _truncate()

### Community 214 - "_ResetsSharedCache"
Cohesion: 0.18
Nodes (3): FallbackTests, _ResetsSharedCache, ToolFacingWrapperTests

## Ambiguous Edges - Review These
- `TTS conversion enhancer prompt (empty)` → `Voice mode tone guidelines`  [AMBIGUOUS]
  prompting/tts_conversion_enhancer_prompt.txt · relation: conceptually_related_to

## Knowledge Gaps
- **165 isolated node(s):** `UserNotifications`, `.serverURLString`, `.summary`, `AudioToolbox`, `.count` (+160 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1587 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **109 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `TTS conversion enhancer prompt (empty)` and `Voice mode tone guidelines`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `NovaGlasses` connect `NovaGlasses` to `XCTestCase`, `SidekickController`, `ConversationController`?**
  _High betweenness centrality (0.314) - this node is a cross-community bridge._
- **Are the 43 inferred relationships involving `AgentLoop` (e.g. with `Server behaviour` and `PromptEnums`) actually correct?**
  _`AgentLoop` has 43 INFERRED edges - model-reasoned connections that need verification._
- **What connects `UserNotifications`, `.serverURLString`, `.summary` to the rest of the system?**
  _165 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `SimpleFinancesService` be split into smaller, more focused modules?**
  _Cohesion score 0.1069182389937107 - nodes in this community are weakly interconnected._
- **Why does `Vision: "Hey Nova, what do you see?"` connect `NovaGlasses` to `VisionService`?**
  _High betweenness centrality (0.314) - this node is a cross-community bridge._
- **Are the 21 inferred relationships involving `Conversation` (e.g. with `_is_stale()` and `ConversationDao`) actually correct?**
  _`Conversation` has 21 INFERRED edges - model-reasoned connections that need verification._