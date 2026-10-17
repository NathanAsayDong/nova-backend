# Graph Report - nova-backend  (2026-10-17)

## Corpus Check
- 214 files · ~173,348 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: (none) 3, .mdc 1, .pbxproj 1)

## Summary
- 4444 nodes · 10381 edges · 217 communities (127 shown, 90 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 1137 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `4d1e965a`
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
- AgentLoopImageTests
- .run_agent
- Update
- make_update
- ClaudeService
- GithubService
- build_service
- Nova system prompt (persona)
- meeting_service.py
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
- UpdateService
- ConversationController
- ElevenLabsService
- HomeView
- test_auth_service.py
- LiveReply
- auth_service.py
- .start
- __main__.py
- VisionService
- test_meeting_service.py
- DATGlassesCamera
- ScheduledTaskService
- build_service
- ResponsibilityService
- Responsibility
- McpOAuthService
- make_update
- build_service
- asr_service.py
- call_controller.py
- McpServer
- CreateScheduleRequirementTests
- sms_controller.py
- test_auth_gate.py
- AuthService
- Project
- TwilioErrorClassificationTests
- ToolTurnSpeechTests
- Meeting
- ConversationLoopStreamTests
- ReplyTests
- SpeechPlayer
- EndpointDecisionTests
- ImageStore
- FakeCamera
- ConversationControllerTests
- ._artifact_for_tool
- test_spoken_reply.py
- ClientEvent
- MacShellTests
- BaseDao
- nova_controller.py
- mcp_oauth_service.py
- AuthenticateTests
- TwilioService
- HttpGateTests
- AgentLoop
- faces_controller.py
- SessionManager
- sidekick_service.py
- .add
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
- TranscriptSegment
- audio_ws.py
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
- sidekick_controller.py
- .init
- PreRollBuffer
- test_asr_filters.py
- FakeDao
- MemoryInjectionTests
- pathlib
- AppModel
- meeting.py
- FakeUpdateService
- host_environment_prompt.py
- APIClient
- Foundation
- Earcon
- SidekickSocketTests
- PromptSourceTests
- EndSessionTests
- SidekickSession
- worker.py
- asr-bench.py
- Link
- os
- ._to_dict
- FakeDao
- ClassificationTests
- CaptureEngine
- FakePlayer
- ToolExecutionError
- SidekickConnection
- WorkingTreeTests
- AudioRouteManager
- .startsWithWakePhrase
- run_migrations.py
- SpokenProse
- TTSService
- RelayTokenTests
- SpeechWakeDetector
- Rig
- clamp_spoken
- PerformTests
- speech_summary
- .iter_sentence_chunks
- GoodbyeTimingTests
- .test_a_live_turn_reads_deltas_then_exposes_the_message
- test_background_agent.py
- WakeDetecting
- FakeMessage
- worktree.py
- PassSentinelTests
- Rig
- CLAUDE.md
- asyncio
- install.sh
- uninstall.sh
- ReportMediumTests
- nova-backend
- shell.py
- CurrentModelTests
- FakeHttp
- BackgroundTests
- DemoService
- EventCodingTests
- match
- VisionRoutesTests
- ConversationControllerTests.swift
- vision_service.py
- ToolServiceTests
- AddPersonView
- AuthStore
- .setUp
- protocol.py
- .look
- BipService
- .wantsToSee
- LookToolExclusionTests
- GlassesSocketTests
- requests
- dict
- XCTestCase
- ClaudeCreditsService
- ASRService
- twilio_service.py
- answer_call
- _receive
- Entry
- ThinkingPulseTests
- TwilioConfigurationError
- get_conversation_messages
- .split_sms_body
- test_settings_service.py
- FakeResponsibilityDao
- _said
- AgentLink
- _PassHold
- MirrorTests
- .allowed_sms_senders
- HostEnvironmentPromptTests
- FakeResponse
- CodingStatus
- FakeUpdateService
- TranscribeUtteranceTests

## God Nodes (most connected - your core abstractions)
1. `AgentLoop` - 104 edges
2. `Conversation` - 79 edges
3. `ConversationController` - 72 edges
4. `ToolService` - 58 edges
5. `build_service()` - 57 edges
6. `MeetingService` - 52 edges
7. `Responsibility` - 47 edges
8. `CodingService` - 47 edges
9. `AppModel` - 43 edges
10. `ServerEvent` - 43 edges

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

## Communities (217 total, 90 thin omitted)

### Community 0 - "Tool"
Cohesion: 0.16
Nodes (5): main(), list_tools(), ToolDao, Tool, FakeToolDao

### Community 1 - "Conversation"
Cohesion: 0.07
Nodes (6): ConversationDao, Conversation, ConversationService, FakeConversationService, FakeConversationService, ThreadResolutionTests

### Community 2 - "SimpleFinancesService"
Cohesion: 0.11
Nodes (6): SimplApiError, SimplConfigurationError, SimpleFinancesService, response(), SimpleFinancesServiceTest, SimplFinancesToolRegistrationTest

### Community 3 - "text"
Cohesion: 0.11
Nodes (8): ToolUseStarted, AuthenticationTests, forward(), make_request(), PathTokenRouteTests, SenderGateTests, go(), text()

### Community 5 - "test_openai_loop.py"
Cohesion: 0.17
Nodes (7): FakeClient, FakeFunctionCall, FakeResponse, FakeResponsesAPI, FakeTool, FakeToolService, OpenAILoopTests

### Community 7 - "AgentLoopImageTests"
Cohesion: 0.33
Nodes (4): AgentLoopImageTests, FakeMessage, FakeTextBlock, FakeToolUseBlock

### Community 8 - ".run_agent"
Cohesion: 0.11
Nodes (3): BackgroundAgentTests, ReportTypeTests, ResponsibilityRunToolRestrictionTests

### Community 9 - "Update"
Cohesion: 0.08
Nodes (4): UpdateDao, Update, _env_int(), UpdateDeliveryService

### Community 10 - "make_update"
Cohesion: 0.14
Nodes (11): at(), BadgeOnlyTests, build_service(), CallDeliveryTests, EmailDeliveryTests, make_update(), QuietHoursTests, SettleCallTests (+3 more)

### Community 11 - "ClaudeService"
Cohesion: 0.09
Nodes (5): _env_flag(), ClaudeService, _env_flag(), GenerationKwargsTests, ClaudeServiceMcpKwargsTests

### Community 12 - "GithubService"
Cohesion: 0.14
Nodes (4): GithubService, GithubServiceError, _FakeResponse, GithubServiceTests

### Community 13 - "build_service"
Cohesion: 0.08
Nodes (8): build_service(), CreateUpdateTests, FakeConversationDao, FakeProjectDao, FakeUpdateDao, make_update(), ReportTypeTests, ViewingTests

### Community 14 - "Nova system prompt (persona)"
Cohesion: 0.07
Nodes (28): Hosting Nova off the home network, Backend environment variables, Cloudflare Tunnel (nova-tower, cloudflared), Firebase Hosting frontend (nova-voice-nd.web.app), Infobip SMS integration (/sms/inbound), Failed-login lockout policy, Mac coding agent (/ws/coding), MCP OAuth callback (+20 more)

### Community 15 - "meeting_service.py"
Cohesion: 0.06
Nodes (5): PromptEnums, EmbeddingService, MemoryChunkService, ParseChunksTests, RetrievableQueryTests

### Community 17 - "Harness"
Cohesion: 0.08
Nodes (19): LevelSmoother, Snapshot, State, calibrating, cooldown, idle, onset, speaking (+11 more)

### Community 19 - "ScheduledTask"
Cohesion: 0.17
Nodes (3): ScheduledTaskDao, ScheduledTask, TaskStatus

### Community 20 - "settings_controller.py"
Cohesion: 0.19
Nodes (4): get_all_settings(), get_available_models(), ModelSwitchRequest, set_model()

### Community 21 - "processes.py"
Cohesion: 0.15
Nodes (16): _all(), await_ready(), check(), _entry(), kill_tree(), _log_paths(), pid_alive(), port_open() (+8 more)

### Community 22 - "process_supervisor.py"
Cohesion: 0.10
Nodes (18): _all(), await_ready(), check(), classify(), _entry(), kill_tree(), _log_paths(), pid_alive() (+10 more)

### Community 23 - "build_service"
Cohesion: 0.09
Nodes (9): build_service(), FakeClaudeResponse, FakeClaudeService, FakeConversationService, FakeEmbeddingService, FakeMemoryChunkDao, FakeTextBlock, FetchMemoryTests (+1 more)

### Community 24 - "MeetingError"
Cohesion: 0.10
Nodes (18): delete_meeting(), get_active_meeting(), get_meeting(), get_meeting_segments(), list_meetings(), _meeting_error(), meeting_socket(), capture_loop() (+10 more)

### Community 25 - "CursorService"
Cohesion: 0.17
Nodes (4): CursorService, CursorServiceError, CursorServiceTests, _FakeResponse

### Community 26 - "MeetingService"
Cohesion: 0.08
Nodes (3): MeetingNotesDao, MeetingNotes, MeetingService

### Community 27 - "FileOperationTests"
Cohesion: 0.09
Nodes (3): EditTests, FileOperationTests, PathContainmentTests

### Community 28 - "CodingSession"
Cohesion: 0.16
Nodes (3): CodingSessionDao, CodingEvent, CodingSession

### Community 29 - "UpdateService"
Cohesion: 0.10
Nodes (5): DeliveryStatus, ReportType, user_phone_number(), UpdateService, EscapingTests

### Community 30 - "ConversationController"
Cohesion: 0.11
Nodes (6): Capture, ConversationController, .isEnabled, .isWorking, .wakeWatching, Once

### Community 31 - "ElevenLabsService"
Cohesion: 0.11
Nodes (7): _describe_failure(), ElevenLabsService, ElevenLabsRequestTests, _env(), FallbackTests, refused(), ProviderSelectionTests

### Community 32 - "HomeView"
Cohesion: 0.08
Nodes (14): ImageIO, NovaGlassesApp, .body, RootView, ImagePrep, AudioLogView, HomeView, .cameraText (+6 more)

### Community 33 - "test_auth_service.py"
Cohesion: 0.10
Nodes (4): NovaSessionDao, row_to_session(), NovaSession, RowConversionTests

### Community 35 - "auth_service.py"
Cohesion: 0.12
Nodes (10): _client_ip(), current_session(), list_sessions(), login(), logout(), logout_all(), AuthNotConfigured, BadCredentials (+2 more)

### Community 37 - "__main__.py"
Cohesion: 0.13
Nodes (7): Config, _flag(), load_env_file(), _configure_logging(), main(), _run(), _task()

### Community 38 - "VisionService"
Cohesion: 0.09
Nodes (8): _allowed_origins(), health(), lifespan(), root(), _broadcast(), face_socket(), VisionService, LookToolTests

### Community 39 - "test_meeting_service.py"
Cohesion: 0.06
Nodes (9): FakeAgentLoop, FakeChunkDao, FakeClaudeService, FakeConversationDao, FakeEmbeddingService, FakeNotesDao, FakeUpdateService, RecoveryTests (+1 more)

### Community 40 - "DATGlassesCamera"
Cohesion: 0.07
Nodes (8): CameraError, .errorDescription, failed, glassesAudioNotUp, noCamera, notReady, timeout, DATGlassesCamera

### Community 42 - "build_service"
Cohesion: 0.18
Nodes (5): build_service(), CreateTests, FakeProjectDao, ListAndCancelTests, soon()

### Community 44 - "Responsibility"
Cohesion: 0.22
Nodes (4): Responsibility, at(), CheckForResponsibilitiesTests, DueTests

### Community 45 - "McpOAuthService"
Cohesion: 0.17
Nodes (6): _b64url(), McpOAuthService, _now(), _origin(), _path(), CompleteAndRefreshTests

### Community 46 - "make_update"
Cohesion: 0.16
Nodes (5): ConversationResolutionTests, make_update(), OpeningPromptTests, TwiMLTests, form()

### Community 47 - "build_service"
Cohesion: 0.07
Nodes (17): MeetingSegment, build_service(), ChunkingTests, CommitSegmentsTests, DeleteMeetingTests, FakeProjectDao, FinalizeTests, FollowUpTests (+9 more)

### Community 48 - "asr_service.py"
Cohesion: 0.20
Nodes (8): main(), _hotwords(), _load_parakeet(), missing_cuda_libraries(), _nvidia_wheel_dll_dirs(), _platform_default_provider(), _resolve_whisper_device(), _setup_cuda_libraries()

### Community 49 - "call_controller.py"
Cohesion: 0.13
Nodes (10): mint_relay_token(), _opening_prompt(), relay_socket(), start_turn(), run_after_previous(), _resolve_conversation_id(), _run_turn(), _signing_key() (+2 more)

### Community 50 - "McpServer"
Cohesion: 0.17
Nodes (3): McpServerDao, McpServer, McpServerService

### Community 52 - "sms_controller.py"
Cohesion: 0.20
Nodes (5): _handle_inbound(), _is_stale(), resolve_sms_conversation(), _run_sms_turn(), ConversationClosedError

### Community 53 - "test_auth_gate.py"
Cohesion: 0.11
Nodes (7): AuthGate, bearer_token(), _header(), is_exempt(), build_app(), ExemptionTests, SidekickAuthTests

### Community 54 - "AuthService"
Cohesion: 0.12
Nodes (3): AuthService, _hash_token(), ConfigurationTests

### Community 55 - "Project"
Cohesion: 0.06
Nodes (8): ProjectDao, Project, CodeService, ProjectService, CodeServiceTestCase, FakeConversationDao, FakeProjectDao, ProjectResolutionTests

### Community 56 - "TwilioErrorClassificationTests"
Cohesion: 0.15
Nodes (6): describe_twilio_error(), is_permanent_twilio_error(), SimpleNamespace_Exception, TwilioErrorClassificationTests, reject(), flake()

### Community 58 - "Meeting"
Cohesion: 0.09
Nodes (3): MeetingDao, Meeting, MeetingStatus

### Community 59 - "ConversationLoopStreamTests"
Cohesion: 0.15
Nodes (5): ConversationLoopStreamTests, fake_stream(), fake_stream(), fake_stream(), EventStreamTests

### Community 61 - "SpeechPlayer"
Cohesion: 0.07
Nodes (7): MP3StreamDecoder, PlaybackWatchdog, SpeechPlayer, .isBusy, .now, Stream, PlaybackWatchdogTests

### Community 62 - "EndpointDecisionTests"
Cohesion: 0.09
Nodes (6): emit_partial_transcript(), endpoint_decision(), _endpoint_scale(), EndpointDecision, silence_budget_ms(), EndpointDecisionTests

### Community 63 - "ImageStore"
Cohesion: 0.16
Nodes (4): ImageStore, VisionImage, ContentBlocksTests, ImageStoreTests

### Community 64 - "FakeCamera"
Cohesion: 0.21
Nodes (4): FakeCamera, FakeVision, settle(), VisionControllerTests

### Community 67 - "test_spoken_reply.py"
Cohesion: 0.16
Nodes (6): _comparable(), is_repeat(), _plain_text(), strip_speak_tags(), IsRepeatTests, StripSpeakTagsTests

### Community 68 - "ClientEvent"
Cohesion: 0.05
Nodes (38): Phase, idle, listening, off, speaking, thinking, PhotoSlot, SocketConnectionState (+30 more)

### Community 70 - "BaseDao"
Cohesion: 0.13
Nodes (3): BaseDao, MessageDao, Message

### Community 71 - "nova_controller.py"
Cohesion: 0.08
Nodes (21): _canonical_wake_text(), get_nova_power(), get_nova_state(), has_stop_phrase(), has_wake_phrase(), normalize_wake_text(), parse_conversation_id(), parse_image_ids() (+13 more)

### Community 73 - "AuthenticateTests"
Cohesion: 0.09
Nodes (4): AuthenticateTests, AuthServiceTestCase, LockoutTests, LoginTests

### Community 76 - "AgentLoop"
Cohesion: 0.03
Nodes (23): PromptSourceEnum, AgentLoop, persist(), ToolService, CountingService, FakeConversationService, FakeToolDao, PrefetchedConversationTests (+15 more)

### Community 77 - "faces_controller.py"
Cohesion: 0.10
Nodes (12): add_sample(), create_person(), delete_person(), _enroll(), list_people(), read_jpeg_body(), upload_image(), DuplicatePerson (+4 more)

### Community 78 - "SessionManager"
Cohesion: 0.20
Nodes (4): _as_int(), _flatten(), _ms_to_iso(), SessionManager

### Community 79 - "sidekick_service.py"
Cohesion: 0.10
Nodes (6): has_be_quiet_phrase(), _normalize(), parse_gate_reply(), SidekickGate, BeQuietPhraseTests, GateReplyTests

### Community 80 - ".add"
Cohesion: 0.12
Nodes (8): EarconPlaying, GlassesCamera, MainScheduler, NovaSocketing, Scheduling, SpeechPlaying, VisionUploading, SidekickController

### Community 82 - "LiveScreenTests"
Cohesion: 0.21
Nodes (3): FakeToolUseBlock, LiveScreenTests, ScriptedTurnStream

### Community 83 - "FakeMcpServerDao"
Cohesion: 0.17
Nodes (3): build_service(), FakeMcpServerDao, McpServerServiceTests

### Community 87 - "Person"
Cohesion: 0.11
Nodes (3): PersonDao, Person, FakePersonDao

### Community 88 - "test_sms.py"
Cohesion: 0.13
Nodes (6): BipConfigurationError, BipRequestError, is_permanent_bip_error(), normalize_phone_number(), SmsRecipientError, NormalizationTests

### Community 89 - "ServerEvent"
Cohesion: 0.07
Nodes (26): ServerEvent, audioStreamChunk, audioStreamEnd, audioStreamStart, captureRequest, chunkReceived, done, error (+18 more)

### Community 90 - "StreamedSpeechTests"
Cohesion: 0.27
Nodes (3): stream(), StreamedSpeechTests, fake_stream()

### Community 92 - "build_memory_service"
Cohesion: 0.26
Nodes (5): build_memory_service(), FakeEmbeddingService, FakeMemoryChunkDao, match(), RetrieveContextTests

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
Nodes (22): Keys, assistantText, bytes, chunkBase64, client, code, conversationId, count (+14 more)

### Community 105 - "FaceService"
Cohesion: 0.13
Nodes (4): FaceService, face_row(), FaceServiceTests, FacesRoutesTests

### Community 106 - "Sendable"
Cohesion: 0.13
Nodes (9): Cancellable, GlassesCameraState, .canCapture, ready, registering, streaming, unavailable, unregistered (+1 more)

### Community 107 - "sidekick_controller.py"
Cohesion: 0.09
Nodes (12): audio_file_bytes(), is_raw_pcm(), _pcm_params(), suffix_for_mime(), transcribe_serialized(), event_source(), sse_event(), run_speculative_transcription() (+4 more)

### Community 109 - "PreRollBuffer"
Cohesion: 0.19
Nodes (4): PCMFormat, PreRollBuffer, .count, AudioFramingTests

### Community 110 - "test_asr_filters.py"
Cohesion: 0.26
Nodes (4): drop_hallucination(), DropHallucinationTests, _segment(), WhisperSegmentFilterTests

### Community 111 - "FakeDao"
Cohesion: 0.23
Nodes (3): ConnectorFilteringTests, FakeDao, oauth_server()

### Community 113 - "pathlib"
Cohesion: 0.18
Nodes (4): _contained(), make_guard(), can_use_tool(), _is_prose()

### Community 114 - "AppModel"
Cohesion: 0.12
Nodes (6): AppModel, .serverURLString, .body, .body, LoginView, .body

### Community 117 - "host_environment_prompt.py"
Cohesion: 0.31
Nodes (3): host_environment_prompt(), _host_kind(), _machine_line()

### Community 118 - "APIClient"
Cohesion: 0.17
Nodes (7): APIClient, APIError, badResponse, .errorDescription, server, unauthorized, Person

### Community 119 - "Foundation"
Cohesion: 0.13
Nodes (8): AudioToolbox, AVFoundation, Foundation, MWDATCamera, MWDATCore, Observation, Speech, UserNotifications

### Community 120 - "Earcon"
Cohesion: 0.11
Nodes (15): Earcons, Note, Earcon, cancel, done, error, shutter, sidekickCue (+7 more)

### Community 121 - "SidekickSocketTests"
Cohesion: 0.15
Nodes (3): GateDecision, SidekickService, SidekickSocketTests

### Community 125 - "worker.py"
Cohesion: 0.27
Nodes (8): build_jobs(), _recover_stuck_tasks(), _run_check_for_responsibilities(), _run_deliver_pending_updates(), _run_process_conversations(), _run_scheduled_tasks(), run_worker(), ScheduledJob

### Community 126 - "asr-bench.py"
Cohesion: 0.21
Nodes (4): cut_clips(), default_audio(), load(), main()

### Community 128 - "os"
Cohesion: 0.07
Nodes (6): MemoryChunkDao, is_sidekick_pass(), MemoryChunk, MemoryMatch, MessageRole, TurnStream

### Community 130 - "FakeDao"
Cohesion: 0.14
Nodes (3): GateTestCase, WebSocketGateTests, FakeDao

### Community 135 - "FakePlayer"
Cohesion: 0.19
Nodes (3): FakePlayer, .isBusy, FakeWake

### Community 137 - "SidekickConnection"
Cohesion: 0.17
Nodes (3): Utterances, sidekick_socket(), SidekickConnection

### Community 139 - "AudioRouteManager"
Cohesion: 0.22
Nodes (3): AudioRouteManager, Route, .summary

### Community 141 - "run_migrations.py"
Cohesion: 0.16
Nodes (4): main(), migration_files(), _jsonable(), SQLService

### Community 143 - "TTSService"
Cohesion: 0.15
Nodes (4): NovaService, OpenAITTS, _requested_provider(), TTSService

### Community 147 - "Rig"
Cohesion: 0.28
Nodes (4): ConversationControllerTests.Rig, Item, ManualScheduler, Rig

### Community 148 - "clamp_spoken"
Cohesion: 0.25
Nodes (4): deliver(), _clamp(), clamp_spoken(), ClampSpokenTests

### Community 153 - ".test_a_live_turn_reads_deltas_then_exposes_the_message"
Cohesion: 0.13
Nodes (4): TurnStreamTests, get_final_message(), __iter__(), get_final_message()

### Community 154 - "test_background_agent.py"
Cohesion: 0.17
Nodes (9): fake_get_response(), FakeConversationService, FakeMessage, FakeProjectDao, FakeTextBlock, FakeToolDao, FakeUpdateService, fake_get_response() (+1 more)

### Community 155 - "WakeDetecting"
Cohesion: 0.15
Nodes (9): WakeDetecting, Build and test (CLI), Code map, How it behaves, Install on your iPhone, NovaGlasses, On-device field checklist, Vision: "Hey Nova, what do you see?" (+1 more)

### Community 156 - "FakeMessage"
Cohesion: 0.20
Nodes (11): FakeMessage, FakeTextBlock, fake_stream(), fake_stream(), fake_stream(), fake_stream(), StatusTextTests, fake_stream() (+3 more)

### Community 157 - "worktree.py"
Cohesion: 0.23
Nodes (7): create(), _git(), remove(), resolve_repo(), slugify(), Workspace, WorktreeError

### Community 158 - "PassSentinelTests"
Cohesion: 0.18
Nodes (7): FakeMessage, FakeTextBlock, FakeToolUseBlock, _live(), get_final_message(), fake_stream(), PassSentinelTests

### Community 159 - "Rig"
Cohesion: 0.21
Nodes (3): Rig, SidekickControllerTests, SidekickEventCodingTests

### Community 161 - "asyncio"
Cohesion: 0.06
Nodes (28): adopt_claude_thread(), _authorized(), coding_socket(), coding_status(), get_coding_session(), list_claude_threads(), list_coding_sessions(), read_claude_thread() (+20 more)

### Community 170 - "shell.py"
Cohesion: 0.15
Nodes (8): classify(), _clip(), _resolve_cwd(), run(), _scratch_pair(), fetch(), main(), sha256()

### Community 172 - "FakeHttp"
Cohesion: 0.25
Nodes (4): build_service(), FakeHttp, InfobipRequestTests, SendSmsTests

### Community 176 - "match"
Cohesion: 0.20
Nodes (5): GalleryPerson, match(), _normalise(), MatchTests, unit()

### Community 177 - "VisionRoutesTests"
Cohesion: 0.26
Nodes (3): Identification, FakeFaceService, VisionRoutesTests

### Community 179 - "vision_service.py"
Cohesion: 0.10
Nodes (8): capture_failed(), CaptureFailed, _in_view_text(), is_image_block(), prepare(), jpeg(), phone(), PrepareTests

### Community 181 - "AddPersonView"
Cohesion: 0.15
Nodes (7): .api, VisionClient, AddPersonView, .body, FacesView, .body, PhotosUI

### Community 182 - "AuthStore"
Cohesion: 0.28
Nodes (3): AuthStore, .baseQuery, Security

### Community 183 - ".setUp"
Cohesion: 0.12
Nodes (4): DirectTurnCounterTests, fake_transcribe(), FakeGate, FakeSidekickLoop

### Community 184 - "protocol.py"
Cohesion: 0.39
Nodes (3): _artifact_for(), encode(), _truncate()

### Community 185 - ".look"
Cohesion: 0.17
Nodes (10): Client → server, Connecting, Deviations from the brief and additions, Interjections, Prompt and tools, Server behaviour, Server → client, Sidekick protocol: `WS /ws/sidekick` (+2 more)

### Community 186 - "BipService"
Cohesion: 0.17
Nodes (3): BipService, _describe_response_error(), _parse_number_list()

### Community 188 - "LookToolExclusionTests"
Cohesion: 0.13
Nodes (4): _agent_loop(), FakeConversationService, FakeToolDao, LookToolExclusionTests

### Community 190 - "requests"
Cohesion: 0.27
Nodes (7): backend_url(), close_current_conversation(), fetch_conversation_info(), fetch_health(), fetch_projects(), fetch_tools(), stream_reply()

### Community 191 - "dict"
Cohesion: 0.25
Nodes (3): basic(), InboundSecretTests, RecipientAllowlistTests

### Community 192 - "XCTestCase"
Cohesion: 0.15
Nodes (3): AudioSessionPolicy, AudioSessionPolicyTests, AmbientForwardingTests

### Community 196 - "answer_call"
Cohesion: 0.27
Nodes (5): answer_call(), call_status(), _escape(), _twiml(), _verified_form()

### Community 197 - "_receive"
Cohesion: 0.31
Nodes (4): _authorize(), inbound_sms(), inbound_sms_with_path_token(), _receive()

### Community 198 - "Entry"
Cohesion: 0.36
Nodes (3): AudioLog, Entry, .body

### Community 201 - "get_conversation_messages"
Cohesion: 0.32
Nodes (4): get_conversation(), get_conversation_messages(), _parse_uuid(), _project_payload()

## Ambiguous Edges - Review These
- `TTS conversion enhancer prompt (empty)` → `Voice mode tone guidelines`  [AMBIGUOUS]
  prompting/tts_conversion_enhancer_prompt.txt · relation: conceptually_related_to

## Knowledge Gaps
- **159 isolated node(s):** `UserNotifications`, `.serverURLString`, `.summary`, `AudioToolbox`, `.count` (+154 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1409 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **90 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `TTS conversion enhancer prompt (empty)` and `Voice mode tone guidelines`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `Vision: "Hey Nova, what do you see?"` connect `WakeDetecting` to `.look`?**
  _High betweenness centrality (0.332) - this node is a cross-community bridge._
- **Are the 37 inferred relationships involving `AgentLoop` (e.g. with `Server behaviour` and `PromptEnums`) actually correct?**
  _`AgentLoop` has 37 INFERRED edges - model-reasoned connections that need verification._
- **What connects `UserNotifications`, `.serverURLString`, `.summary` to the rest of the system?**
  _159 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Conversation` be split into smaller, more focused modules?**
  _Cohesion score 0.07247223845704266 - nodes in this community are weakly interconnected._
- **Why does `Build and test (CLI)` connect `WakeDetecting` to `Harness`, `ConversationController`?**
  _High betweenness centrality (0.296) - this node is a cross-community bridge._
- **Are the 18 inferred relationships involving `Conversation` (e.g. with `_is_stale()` and `ConversationDao`) actually correct?**
  _`Conversation` has 18 INFERRED edges - model-reasoned connections that need verification._