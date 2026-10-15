# Graph Report - nova-backend  (2026-10-15)

## Corpus Check
- 205 files · ~160,757 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 10 file(s) not represented in the graph (top: (none) 3, .mdc 1, .pbxproj 1)

## Summary
- 4121 nodes · 9557 edges · 194 communities (107 shown, 87 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 1017 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `fbe34937`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Tool
- Conversation
- SimpleFinancesService
- text
- TranscribeSocketTests
- test_openai_loop.py
- CommandLineService
- test_vision.py
- .run_agent
- UpdateDeliveryService
- make_update
- ClaudeService
- GithubService
- build_service
- Nova system prompt (persona)
- MemoryChunkService
- CurrentModelTests
- Harness
- CodingService
- ScheduledTask
- settings_controller.py
- processes.py
- process_supervisor.py
- build_service
- MeetingError
- CursorService
- MeetingService
- FileOperationTests
- CodingSession
- Update
- ConversationController
- ElevenLabsService
- Project
- NovaSession
- LiveReply
- asyncio
- .start
- __main__.py
- nova_controller.py
- FakeAgentLoop
- DATGlassesCamera
- ScheduledTaskService
- build_service
- ResponsibilityService
- Responsibility
- McpOAuthService
- make_update
- build_service
- pathlib
- call_controller.py
- McpServerService
- CreateScheduleRequirementTests
- FakeHttp
- auth_service.py
- AuthService
- CodeService
- TwilioErrorClassificationTests
- FakeMessage
- _receive
- .completed
- ReplyTests
- SpeechPlayer
- EndpointDecisionTests
- ImageStore
- MirrorTests
- Rig
- ._artifact_for_tool
- test_spoken_reply.py
- ClientEvent
- MacShellTests
- AppModel
- fetch_face_models.py
- McpServer
- AuthenticateTests
- TwilioService
- HttpGateTests
- AgentLoop
- faces_controller.py
- SessionManager
- Equatable
- String
- SpokenTrackTests
- LiveScreenTests
- FakeMcpServerDao
- FakeMeetingDao
- CrudTests
- SettingsService
- Person
- test_sms.py
- ServerEvent
- StreamedSpeechTests
- AgentBindingTests
- build_memory_service
- test_responsibility_service.py
- ASRService
- AsrLock
- pending
- Mac code agent daemon
- FakeTaskDao
- ServiceMethodToolConfig
- FailureSpeechTests
- ._run_begin
- email_service.py
- NovaSocket
- Keys
- FaceService
- Sendable
- test_glasses_voice.py
- .ingest
- PreRollBuffer
- test_asr_filters.py
- FakeDao
- MemoryInjectionTests
- sessions.py
- HomeView
- meeting_service.py
- FakeUpdateService
- host_environment_prompt.py
- APIClient
- Foundation
- Earcon
- PromptSourceTests
- EndSessionTests
- FakeConversationService
- worker.py
- asr-bench.py
- Link
- os
- ._to_dict
- FakeDao
- ClassificationTests
- CaptureEngine
- FakeSocket
- ToolService
- MP3StreamDecoder
- WorkingTreeTests
- AudioRouteManager
- .startsWithWakePhrase
- run_migrations.py
- SpokenProse
- TTSService
- RelayTokenTests
- SpeechWakeDetector
- Double
- clamp_spoken
- PerformTests
- speech_summary
- .iter_sentence_chunks
- GoodbyeTimingTests
- .test_a_live_turn_refuses_a_second_read
- .setUp
- NovaGlasses
- StatusTextTests
- AgentLoopMcpTests
- project_service.py
- PlaybackWatchdog
- CLAUDE.md
- conversation_controller.py
- install.sh
- uninstall.sh
- ReportMediumTests
- nova-backend
- FakeResponsibilityDao
- _said
- .test_a_live_turn_reads_deltas_then_exposes_the_message
- .get_current_time
- DemoService
- CodingStatus
- match
- VisionRoutesTests
- .identify
- FaceServiceTests
- Entry
- VisionClient
- FakePersonDao
- .scaled
- AgentLink
- .setUp
- FakeConversationService
- VisionIntent
- .transcript
- build_app
- ThreadResolutionTests
- HostEnvironmentPromptTests
- FakeChunkDao
- FakeConversationService

## God Nodes (most connected - your core abstractions)
1. `AgentLoop` - 99 edges
2. `Conversation` - 76 edges
3. `ConversationController` - 62 edges
4. `build_service()` - 57 edges
5. `ToolService` - 53 edges
6. `MeetingService` - 52 edges
7. `Responsibility` - 47 edges
8. `CodingService` - 47 edges
9. `Update` - 42 edges
10. `UpdateService` - 42 edges

## Surprising Connections (you probably didn't know these)
- `Build and test (CLI)` --references--> `ConversationController`  [INFERRED]
  ios/NovaGlasses/README.md → ios/NovaGlasses/NovaGlasses/Conversation/ConversationController.swift
- `Code map` --references--> `WakeDetecting`  [INFERRED]
  ios/NovaGlasses/README.md → ios/NovaGlasses/NovaGlasses/Conversation/Ports.swift
- `Build and test (CLI)` --references--> `TurnDetector`  [INFERRED]
  ios/NovaGlasses/README.md → ios/NovaGlasses/NovaGlasses/Voice/TurnDetector.swift
- `lifespan()` --uses--> `VisionService`  [INFERRED]
  main.py → src/service/vision_service.py
- `AgentLoop` --uses--> `PromptEnums`  [INFERRED]
  src/harness/agent_loop.py → prompting/prompt_enums.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Remote access path: Firebase frontend to Cloudflare Tunnel to tower API** — docs_hosting_firebase_hosting, docs_hosting_cloudflare_tunnel, docs_hosting_tower_api [EXTRACTED 0.95]
- **Mac agent core design principles** — mac_agent_readme_dial_out, mac_agent_readme_sessions_as_threads, mac_agent_readme_git_worktree [EXTRACTED 1.00]
- **Persisted-action safety rules across foreground and background agents** — prompting_nova_persona_prompt_confirm_persisted_actions, prompting_nova_persona_prompt_clarify_before_executing, prompting_background_agent_prompt_no_outward_actions [INFERRED 0.85]

## Communities (194 total, 87 thin omitted)

### Community 0 - "Tool"
Cohesion: 0.13
Nodes (5): list_tools(), ToolDao, Tool, FakeToolDao, ToolServiceTests

### Community 1 - "Conversation"
Cohesion: 0.08
Nodes (3): ConversationDao, Conversation, ConversationService

### Community 2 - "SimpleFinancesService"
Cohesion: 0.11
Nodes (6): SimplApiError, SimplConfigurationError, SimpleFinancesService, response(), SimpleFinancesServiceTest, SimplFinancesToolRegistrationTest

### Community 3 - "text"
Cohesion: 0.09
Nodes (11): _artifact_for(), encode(), _truncate(), ToolUseStarted, AuthenticationTests, forward(), make_request(), PathTokenRouteTests (+3 more)

### Community 5 - "test_openai_loop.py"
Cohesion: 0.16
Nodes (7): FakeClient, FakeFunctionCall, FakeResponse, FakeResponsesAPI, FakeTool, FakeToolService, OpenAILoopTests

### Community 6 - "CommandLineService"
Cohesion: 0.07
Nodes (3): CommandLineService, BackgroundTests, ForegroundTests

### Community 7 - "test_vision.py"
Cohesion: 0.06
Nodes (12): ToolExecutionError, _in_view_text(), InvalidImage, is_image_block(), prepare(), AgentLoopImageTests, FakeMessage, FakeTextBlock (+4 more)

### Community 8 - ".run_agent"
Cohesion: 0.11
Nodes (3): BackgroundAgentTests, ReportTypeTests, ResponsibilityRunToolRestrictionTests

### Community 10 - "make_update"
Cohesion: 0.14
Nodes (11): at(), BadgeOnlyTests, build_service(), CallDeliveryTests, EmailDeliveryTests, make_update(), QuietHoursTests, SettleCallTests (+3 more)

### Community 11 - "ClaudeService"
Cohesion: 0.12
Nodes (3): ClaudeService, GenerationKwargsTests, ClaudeServiceMcpKwargsTests

### Community 12 - "GithubService"
Cohesion: 0.15
Nodes (4): GithubService, GithubServiceError, _FakeResponse, GithubServiceTests

### Community 13 - "build_service"
Cohesion: 0.08
Nodes (8): build_service(), CreateUpdateTests, FakeConversationDao, FakeProjectDao, FakeUpdateDao, make_update(), ReportTypeTests, ViewingTests

### Community 14 - "Nova system prompt (persona)"
Cohesion: 0.07
Nodes (28): Hosting Nova off the home network, Backend environment variables, Cloudflare Tunnel (nova-tower, cloudflared), Firebase Hosting frontend (nova-voice-nd.web.app), Infobip SMS integration (/sms/inbound), Failed-login lockout policy, Mac coding agent (/ws/coding), MCP OAuth callback (+20 more)

### Community 15 - "MemoryChunkService"
Cohesion: 0.07
Nodes (7): MemoryChunkDao, MemoryChunk, MemoryMatch, EmbeddingService, MemoryChunkService, ParseChunksTests, RetrievableQueryTests

### Community 17 - "Harness"
Cohesion: 0.10
Nodes (10): LevelSmoother, TurnDetector, .closeThreshold, .openThreshold, TurnEndReason, maxDuration, silence, steadyNoise (+2 more)

### Community 19 - "ScheduledTask"
Cohesion: 0.12
Nodes (4): ScheduledTaskDao, ScheduledTask, FakeProjectDao, FakeUpdateService

### Community 20 - "settings_controller.py"
Cohesion: 0.10
Nodes (6): get_all_settings(), get_available_models(), get_claude_credits(), ModelSwitchRequest, set_model(), ClaudeCreditsService

### Community 21 - "processes.py"
Cohesion: 0.11
Nodes (21): _all(), await_ready(), check(), classify(), _entry(), kill_tree(), _log_paths(), pid_alive() (+13 more)

### Community 22 - "process_supervisor.py"
Cohesion: 0.07
Nodes (25): create(), _git(), remove(), resolve_repo(), slugify(), Workspace, WorktreeError, _all() (+17 more)

### Community 23 - "build_service"
Cohesion: 0.12
Nodes (6): build_service(), FakeConversationService, FakeEmbeddingService, FakeMemoryChunkDao, FetchMemoryTests, ProcessConversationsTests

### Community 24 - "MeetingError"
Cohesion: 0.09
Nodes (19): transcribe_segments_serialized(), delete_meeting(), get_active_meeting(), get_meeting(), get_meeting_segments(), list_meetings(), _meeting_error(), meeting_socket() (+11 more)

### Community 25 - "CursorService"
Cohesion: 0.11
Nodes (11): backend_url(), close_current_conversation(), fetch_conversation_info(), fetch_health(), fetch_projects(), fetch_tools(), stream_reply(), CursorService (+3 more)

### Community 26 - "MeetingService"
Cohesion: 0.05
Nodes (4): MeetingDao, Meeting, MeetingNotes, MeetingService

### Community 27 - "FileOperationTests"
Cohesion: 0.09
Nodes (4): CodeServiceTestCase, EditTests, FileOperationTests, PathContainmentTests

### Community 28 - "CodingSession"
Cohesion: 0.16
Nodes (3): CodingSessionDao, CodingEvent, CodingSession

### Community 29 - "Update"
Cohesion: 0.07
Nodes (6): UpdateDao, DeliveryStatus, ReportType, Update, UpdateService, EscapingTests

### Community 30 - "ConversationController"
Cohesion: 0.12
Nodes (6): Capture, ConversationController, .isEnabled, .wakeWatching, Once, NovaSocketing

### Community 31 - "ElevenLabsService"
Cohesion: 0.11
Nodes (7): _describe_failure(), ElevenLabsService, ElevenLabsRequestTests, _env(), FallbackTests, refused(), ProviderSelectionTests

### Community 32 - "Project"
Cohesion: 0.13
Nodes (3): Project, ProjectService, ProjectResolutionTests

### Community 33 - "NovaSession"
Cohesion: 0.09
Nodes (4): NovaSessionDao, row_to_session(), NovaSession, RowConversionTests

### Community 35 - "asyncio"
Cohesion: 0.04
Nodes (40): _allowed_origins(), lifespan(), _client_ip(), current_session(), list_sessions(), login(), logout(), logout_all() (+32 more)

### Community 37 - "__main__.py"
Cohesion: 0.13
Nodes (7): Config, _flag(), load_env_file(), _configure_logging(), main(), _run(), _task()

### Community 38 - "nova_controller.py"
Cohesion: 0.05
Nodes (27): _canonical_wake_text(), chat_stream(), event_source(), get_nova_power(), get_nova_state(), has_stop_phrase(), has_wake_phrase(), normalize_wake_text() (+19 more)

### Community 39 - "FakeAgentLoop"
Cohesion: 0.10
Nodes (4): FakeAgentLoop, FakeClaudeService, FakeNotesDao, ReplyQueue

### Community 40 - "DATGlassesCamera"
Cohesion: 0.09
Nodes (8): CameraError, .errorDescription, failed, glassesAudioNotUp, noCamera, notReady, timeout, DATGlassesCamera

### Community 42 - "build_service"
Cohesion: 0.21
Nodes (4): build_service(), CreateTests, ListAndCancelTests, soon()

### Community 44 - "Responsibility"
Cohesion: 0.16
Nodes (4): Responsibility, at(), CheckForResponsibilitiesTests, DueTests

### Community 45 - "McpOAuthService"
Cohesion: 0.22
Nodes (4): _b64url(), McpOAuthService, _origin(), _path()

### Community 46 - "make_update"
Cohesion: 0.16
Nodes (5): ConversationResolutionTests, make_update(), OpeningPromptTests, TwiMLTests, form()

### Community 47 - "build_service"
Cohesion: 0.06
Nodes (21): MeetingSegment, build_service(), ChunkingTests, CommitSegmentsTests, DeleteMeetingTests, FakeConversationDao, FakeEmbeddingService, FakeProjectDao (+13 more)

### Community 48 - "pathlib"
Cohesion: 0.19
Nodes (8): main(), _hotwords(), _load_parakeet(), missing_cuda_libraries(), _nvidia_wheel_dll_dirs(), _platform_default_provider(), _resolve_whisper_device(), _setup_cuda_libraries()

### Community 49 - "call_controller.py"
Cohesion: 0.08
Nodes (16): answer_call(), call_status(), _escape(), mint_relay_token(), _opening_prompt(), relay_socket(), start_turn(), run_after_previous() (+8 more)

### Community 52 - "FakeHttp"
Cohesion: 0.12
Nodes (8): basic(), build_service(), FakeHttp, FakeResponse, InboundSecretTests, InfobipRequestTests, RecipientAllowlistTests, SendSmsTests

### Community 53 - "auth_service.py"
Cohesion: 0.16
Nodes (5): AuthGate, bearer_token(), _header(), is_exempt(), ExemptionTests

### Community 54 - "AuthService"
Cohesion: 0.13
Nodes (4): AuthService, _hash_token(), _now(), ConfigurationTests

### Community 56 - "TwilioErrorClassificationTests"
Cohesion: 0.15
Nodes (6): describe_twilio_error(), is_permanent_twilio_error(), SimpleNamespace_Exception, TwilioErrorClassificationTests, reject(), flake()

### Community 57 - "FakeMessage"
Cohesion: 0.24
Nodes (5): FakeMessage, FakeTextBlock, fake_stream(), fake_stream(), ToolTurnSpeechTests

### Community 58 - "_receive"
Cohesion: 0.31
Nodes (4): _authorize(), inbound_sms(), inbound_sms_with_path_token(), _receive()

### Community 59 - ".completed"
Cohesion: 0.12
Nodes (7): ConversationLoopStreamTests, fake_stream(), fake_stream(), fake_stream(), EventStreamTests, fake_stream(), fake_stream()

### Community 61 - "SpeechPlayer"
Cohesion: 0.16
Nodes (4): SpeechPlayer, .isBusy, .now, Stream

### Community 63 - "ImageStore"
Cohesion: 0.10
Nodes (6): CaptureFailed, ImageStore, VisionImage, GlassesSocketTests, ContentBlocksTests, ImageStoreTests

### Community 67 - "test_spoken_reply.py"
Cohesion: 0.17
Nodes (6): deliver(), _comparable(), is_repeat(), strip_speak_tags(), IsRepeatTests, StripSpeakTagsTests

### Community 68 - "ClientEvent"
Cohesion: 0.09
Nodes (19): AudioRole, final, progress, status, wake, CapturePurpose, sentry, turn (+11 more)

### Community 70 - "AppModel"
Cohesion: 0.14
Nodes (3): AppModel, .serverURLString, .body

### Community 71 - "fetch_face_models.py"
Cohesion: 0.36
Nodes (3): fetch(), main(), sha256()

### Community 72 - "McpServer"
Cohesion: 0.20
Nodes (3): McpServer, _now(), _parse_expiry()

### Community 73 - "AuthenticateTests"
Cohesion: 0.09
Nodes (4): AuthenticateTests, AuthServiceTestCase, LockoutTests, LoginTests

### Community 74 - "TwilioService"
Cohesion: 0.09
Nodes (5): main(), report(), TwilioConfigurationError, TwilioService, ConfigurationGuardTests

### Community 76 - "AgentLoop"
Cohesion: 0.05
Nodes (6): PromptSourceEnum, AgentLoop, persist(), _env_flag(), PrefetchedConversationTests, GlassesPromptSourceTests

### Community 77 - "faces_controller.py"
Cohesion: 0.12
Nodes (10): add_sample(), create_person(), delete_person(), _enroll(), list_people(), read_jpeg_body(), DuplicatePerson, EnrollmentError (+2 more)

### Community 78 - "SessionManager"
Cohesion: 0.27
Nodes (3): _as_int(), _ms_to_iso(), SessionManager

### Community 79 - "Equatable"
Cohesion: 0.13
Nodes (15): Phase, idle, listening, off, speaking, thinking, Snapshot, State (+7 more)

### Community 80 - "String"
Cohesion: 0.15
Nodes (6): PhotoSlot, GlassesCamera, SpeechPlaying, VisionUploading, WakeDetecting, Code map

### Community 81 - "SpokenTrackTests"
Cohesion: 0.23
Nodes (3): FakeToolUseBlock, SpokenTrackTests, fake_stream()

### Community 83 - "FakeMcpServerDao"
Cohesion: 0.17
Nodes (3): build_service(), FakeMcpServerDao, McpServerServiceTests

### Community 86 - "SettingsService"
Cohesion: 0.11
Nodes (3): SettingsService, ModelListTests, _ResetsSharedState

### Community 88 - "test_sms.py"
Cohesion: 0.06
Nodes (13): _handle_inbound(), BipConfigurationError, BipRequestError, BipService, _describe_response_error(), is_permanent_bip_error(), normalize_phone_number(), _parse_number_list() (+5 more)

### Community 89 - "ServerEvent"
Cohesion: 0.08
Nodes (21): ServerEvent, audioStreamChunk, audioStreamEnd, audioStreamStart, captureRequest, chunkReceived, done, error (+13 more)

### Community 90 - "StreamedSpeechTests"
Cohesion: 0.27
Nodes (3): stream(), StreamedSpeechTests, fake_stream()

### Community 92 - "build_memory_service"
Cohesion: 0.18
Nodes (6): build_memory_service(), FakeConversationService, FakeEmbeddingService, FakeMemoryChunkDao, match(), RetrieveContextTests

### Community 93 - "test_responsibility_service.py"
Cohesion: 0.19
Nodes (4): build_service(), FakeProjectDao, FakeUpdateService, WindowTests

### Community 96 - "pending"
Cohesion: 0.22
Nodes (4): pending(), RecoverStuckTests, RunDueTests, RunTests

### Community 97 - "Mac code agent daemon"
Cohesion: 0.16
Nodes (14): Nova code agent (Mac) README, Anthropic API key stripping, Mac dials out design, Per-session git worktree, Known limits (awake Mac, bounded replay, cache cost), launchd install and menu app, Mac code agent daemon, NOVA_CODE_TOKEN shared secret (+6 more)

### Community 101 - "._run_begin"
Cohesion: 0.23
Nodes (6): BeginFlowTests, fake_get(), fake_post(), fake_post(), fake_post(), FakeResponse

### Community 104 - "Keys"
Cohesion: 0.09
Nodes (21): Keys, assistantText, bytes, chunkBase64, client, code, conversationId, count (+13 more)

### Community 106 - "Sendable"
Cohesion: 0.11
Nodes (16): Cancellable, GlassesCameraState, .canCapture, ready, registering, streaming, unavailable, unregistered (+8 more)

### Community 107 - "test_glasses_voice.py"
Cohesion: 0.07
Nodes (13): audio_file_bytes(), is_raw_pcm(), _pcm_params(), suffix_for_mime(), transcribe_serialized(), emit_partial_transcript(), run_speculative_transcription(), endpoint_decision() (+5 more)

### Community 109 - "PreRollBuffer"
Cohesion: 0.20
Nodes (4): PCMFormat, PreRollBuffer, .count, AudioFramingTests

### Community 110 - "test_asr_filters.py"
Cohesion: 0.26
Nodes (4): drop_hallucination(), DropHallucinationTests, _segment(), WhisperSegmentFilterTests

### Community 111 - "FakeDao"
Cohesion: 0.18
Nodes (4): CompleteAndRefreshTests, ConnectorFilteringTests, FakeDao, oauth_server()

### Community 112 - "MemoryInjectionTests"
Cohesion: 0.20
Nodes (5): FakeMessage, FakeTextBlock, FakeToolDao, MemoryInjectionTests, fake_stream()

### Community 113 - "sessions.py"
Cohesion: 0.16
Nodes (5): _contained(), make_guard(), can_use_tool(), health(), root()

### Community 114 - "HomeView"
Cohesion: 0.07
Nodes (17): NovaGlassesApp, .body, RootView, .body, AuthStore, .baseQuery, AudioLogView, HomeView (+9 more)

### Community 115 - "meeting_service.py"
Cohesion: 0.07
Nodes (8): PromptEnums, BaseDao, MeetingChunkDao, MeetingNotesDao, ProjectDao, ResponsibilityDao, MeetingChunk, MeetingStatus

### Community 117 - "host_environment_prompt.py"
Cohesion: 0.31
Nodes (3): host_environment_prompt(), _host_kind(), _machine_line()

### Community 118 - "APIClient"
Cohesion: 0.15
Nodes (7): APIClient, APIError, badResponse, .errorDescription, server, unauthorized, Person

### Community 119 - "Foundation"
Cohesion: 0.10
Nodes (10): AudioToolbox, AVFoundation, Foundation, MWDATCamera, MWDATCore, NovaGlasses, Observation, Speech (+2 more)

### Community 120 - "Earcon"
Cohesion: 0.15
Nodes (11): Earcons, Note, Earcon, cancel, done, error, shutter, thinking (+3 more)

### Community 124 - "FakeConversationService"
Cohesion: 0.16
Nodes (4): CountingService, FakeConversationService, FakeToolDao, fake_stream()

### Community 125 - "worker.py"
Cohesion: 0.27
Nodes (8): build_jobs(), _recover_stuck_tasks(), _run_check_for_responsibilities(), _run_deliver_pending_updates(), _run_process_conversations(), _run_scheduled_tasks(), run_worker(), ScheduledJob

### Community 126 - "asr-bench.py"
Cohesion: 0.36
Nodes (4): cut_clips(), default_audio(), load(), main()

### Community 128 - "os"
Cohesion: 0.07
Nodes (13): _is_stale(), resolve_sms_conversation(), _run_sms_turn(), Message, MessageRole, _env_flag(), TurnStream, ConversationClosedError (+5 more)

### Community 130 - "FakeDao"
Cohesion: 0.14
Nodes (3): GateTestCase, WebSocketGateTests, FakeDao

### Community 135 - "FakeSocket"
Cohesion: 0.13
Nodes (5): FakePlayer, .isBusy, FakeSocket, .starts, FakeWake

### Community 136 - "ToolService"
Cohesion: 0.28
Nodes (3): main(), main(), ToolService

### Community 139 - "AudioRouteManager"
Cohesion: 0.12
Nodes (6): AudioRouteManager, .hasGlassesInput, Route, .summary, AudioSessionPolicy, AudioSessionPolicyTests

### Community 141 - "run_migrations.py"
Cohesion: 0.16
Nodes (4): main(), migration_files(), _jsonable(), SQLService

### Community 143 - "TTSService"
Cohesion: 0.15
Nodes (4): NovaService, OpenAITTS, _requested_provider(), TTSService

### Community 147 - "Double"
Cohesion: 0.29
Nodes (3): ConversationControllerTests.Rig, Item, ManualScheduler

### Community 148 - "clamp_spoken"
Cohesion: 0.29
Nodes (3): _clamp(), clamp_spoken(), ClampSpokenTests

### Community 154 - ".setUp"
Cohesion: 0.17
Nodes (8): fake_get_response(), FakeConversationService, FakeMessage, FakeTextBlock, FakeToolDao, FakeUpdateService, fake_get_response(), _schema_tool()

### Community 155 - "NovaGlasses"
Cohesion: 0.29
Nodes (6): Build and test (CLI), How it behaves, Install on your iPhone, NovaGlasses, On-device field checklist, What is verified and what is not

### Community 157 - "AgentLoopMcpTests"
Cohesion: 0.18
Nodes (7): AgentLoopMcpTests, fake_stream(), fake_stream(), FakeBlock, FakeMcpService, FakeMessage, FakeToolDao

### Community 161 - "conversation_controller.py"
Cohesion: 0.27
Nodes (5): close_conversation(), get_conversation(), get_conversation_messages(), _parse_uuid(), _project_payload()

### Community 176 - "match"
Cohesion: 0.35
Nodes (4): GalleryPerson, match(), MatchTests, unit()

### Community 177 - "VisionRoutesTests"
Cohesion: 0.26
Nodes (3): Identification, FakeFaceService, VisionRoutesTests

### Community 180 - "Entry"
Cohesion: 0.36
Nodes (3): AudioLog, Entry, .body

## Ambiguous Edges - Review These
- `TTS conversion enhancer prompt (empty)` → `Voice mode tone guidelines`  [AMBIGUOUS]
  prompting/tts_conversion_enhancer_prompt.txt · relation: conceptually_related_to

## Knowledge Gaps
- **138 isolated node(s):** `UserNotifications`, `.serverURLString`, `.summary`, `.hasGlassesInput`, `AudioToolbox` (+133 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1308 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **87 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `TTS conversion enhancer prompt (empty)` and `Voice mode tone guidelines`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `AgentLoop` connect `AgentLoop` to `os`, `Conversation`, `test_vision.py`, `.run_agent`, `ToolService`, `ClaudeService`, `MemoryChunkService`, `ScheduledTask`, `.iter_sentence_chunks`, `MeetingService`, `.setUp`, `Update`, `AgentLoopMcpTests`, `LiveReply`, `nova_controller.py`, `ScheduledTaskService`, `ResponsibilityService`, `call_controller.py`, `McpServerService`, `FakeMessage`, `FakeConversationService`, `.completed`, `._artifact_for_tool`, `SpokenTrackTests`, `LiveScreenTests`, `StreamedSpeechTests`, `FailureSpeechTests`, `test_glasses_voice.py`, `MemoryInjectionTests`, `meeting_service.py`, `FakeConversationService`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Are the 35 inferred relationships involving `AgentLoop` (e.g. with `PromptEnums` and `PromptSourceEnum`) actually correct?**
  _`AgentLoop` has 35 INFERRED edges - model-reasoned connections that need verification._
- **What connects `UserNotifications`, `.serverURLString`, `.summary` to the rest of the system?**
  _138 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Tool` be split into smaller, more focused modules?**
  _Cohesion score 0.13368983957219252 - nodes in this community are weakly interconnected._
- **Why does `ClaudeService` connect `ClaudeService` to `os`, `AgentLoop`, `MemoryChunkService`, `CurrentModelTests`, `.get_available_models`, `meeting_service.py`, `settings_controller.py`, `SettingsService`, `MeetingService`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._
- **Are the 17 inferred relationships involving `Conversation` (e.g. with `_is_stale()` and `ConversationDao`) actually correct?**
  _`Conversation` has 17 INFERRED edges - model-reasoned connections that need verification._