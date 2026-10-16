# Graph Report - nova-backend  (2026-10-16)

## Corpus Check
- 207 files · ~163,507 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: (none) 3, .mdc 1, .pbxproj 1)

## Summary
- 4184 nodes · 9769 edges · 193 communities (115 shown, 78 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 1058 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `bbf0cd3e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Tool
- Conversation
- SimpleFinancesService
- post
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
- test_auth_service.py
- LiveReply
- auth_controller.py
- SessionManager
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
- McpServerService
- CreateScheduleRequirementTests
- nova_controller.py
- test_auth_gate.py
- AuthService
- ProjectDao
- TwilioErrorClassificationTests
- FakeTextBlock
- Meeting
- ConversationLoopStreamTests
- ReplyTests
- SpeechPlayer
- EndpointDecisionTests
- ImageStore
- FakeCamera
- Rig
- ._artifact_for_tool
- test_spoken_reply.py
- ClientEvent
- MacShellTests
- BaseDao
- re
- McpServer
- FakeDao
- TwilioService
- HttpGateTests
- AgentLoop
- faces_controller.py
- Any
- transcribe_socket
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
- test_memory_injection.py
- test_responsibility_service.py
- ASRService
- AsrLock
- pending
- Mac code agent daemon
- FakeTaskDao
- ServiceMethodToolConfig
- FailureSpeechTests
- ._run_begin
- NovaSocket
- Keys
- FaceService
- Sendable
- pathlib
- GlassesCameraState
- PreRollBuffer
- test_asr_filters.py
- FakeDao
- MemoryInjectionTests
- sessions.py
- AppModel
- meeting_service.py
- FakeUpdateService
- host_environment_prompt.py
- APIClient
- Foundation
- Earcon
- PromptSourceTests
- EndSessionTests
- main.py
- worker.py
- asr-bench.py
- Link
- agent_loop.py
- ._to_dict
- WebSocketGateTests
- test_process_supervisor.py
- CaptureEngine
- FakePlayer
- ToolExecutionError
- WorkingTreeTests
- .add
- .startsWithWakePhrase
- run_migrations.py
- SpokenProse
- TTSService
- RelayTokenTests
- SpeechWakeDetector
- Double
- ._conversation_turn
- PerformTests
- speech_summary
- .iter_sentence_chunks
- GoodbyeTimingTests
- .completed
- .setUp
- WakeDetecting
- FakeMessage
- worktree.py
- mcp_server_controller.py
- CLAUDE.md
- asyncio
- install.sh
- uninstall.sh
- ReportMediumTests
- nova-backend
- os
- CurrentModelTests
- .test_a_live_turn_reads_deltas_then_exposes_the_message
- .get_current_time
- DemoService
- .json
- match
- VisionRoutesTests
- ConversationControllerTests.swift
- prepare
- ToolServiceTests
- AddPersonView
- AuthStore
- FallbackTests
- protocol.py
- CodeServiceTestCase
- PathContainmentTests
- XCTestCase
- ProjectResolutionTests
- FakeAgentLoop
- RunTests
- LoginTests

## God Nodes (most connected - your core abstractions)
1. `AgentLoop` - 101 edges
2. `Conversation` - 76 edges
3. `ConversationController` - 67 edges
4. `build_service()` - 57 edges
5. `ToolService` - 56 edges
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
- `encode()` --indirect_call--> `text()`  [INFERRED]
  mac_agent/novacode/protocol.py → tests/test_sms_controller.py
- `lifespan()` --uses--> `VisionService`  [INFERRED]
  main.py → src/service/vision_service.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Remote access path: Firebase frontend to Cloudflare Tunnel to tower API** — docs_hosting_firebase_hosting, docs_hosting_cloudflare_tunnel, docs_hosting_tower_api [EXTRACTED 0.95]
- **Mac agent core design principles** — mac_agent_readme_dial_out, mac_agent_readme_sessions_as_threads, mac_agent_readme_git_worktree [EXTRACTED 1.00]
- **Persisted-action safety rules across foreground and background agents** — prompting_nova_persona_prompt_confirm_persisted_actions, prompting_nova_persona_prompt_clarify_before_executing, prompting_background_agent_prompt_no_outward_actions [INFERRED 0.85]

## Communities (193 total, 78 thin omitted)

### Community 0 - "Tool"
Cohesion: 0.13
Nodes (5): list_tools(), ToolDao, Tool, _schema_tool(), FakeToolDao

### Community 1 - "Conversation"
Cohesion: 0.08
Nodes (5): ConversationDao, Conversation, ConversationService, FakeConversationService, ThreadResolutionTests

### Community 2 - "SimpleFinancesService"
Cohesion: 0.11
Nodes (6): SimplApiError, SimplConfigurationError, SimpleFinancesService, response(), SimpleFinancesServiceTest, SimplFinancesToolRegistrationTest

### Community 3 - "post"
Cohesion: 0.05
Nodes (24): adopt_claude_thread(), AgentLink, coding_status(), get_coding_session(), list_claude_threads(), list_coding_sessions(), read_claude_thread(), send_coding_feedback() (+16 more)

### Community 5 - "test_openai_loop.py"
Cohesion: 0.18
Nodes (7): FakeClient, FakeFunctionCall, FakeResponse, FakeResponsesAPI, FakeTool, FakeToolService, OpenAILoopTests

### Community 6 - "CommandLineService"
Cohesion: 0.07
Nodes (3): CommandLineService, BackgroundTests, ForegroundTests

### Community 7 - "test_vision.py"
Cohesion: 0.07
Nodes (6): HostEnvironmentPromptTests, AgentLoopImageTests, FakeConversationService, FakeMessage, FakeTextBlock, FakeToolUseBlock

### Community 8 - ".run_agent"
Cohesion: 0.11
Nodes (3): BackgroundAgentTests, ReportTypeTests, ResponsibilityRunToolRestrictionTests

### Community 9 - "UpdateDeliveryService"
Cohesion: 0.15
Nodes (3): EmailService, _env_int(), UpdateDeliveryService

### Community 10 - "make_update"
Cohesion: 0.13
Nodes (11): at(), BadgeOnlyTests, build_service(), CallDeliveryTests, EmailDeliveryTests, make_update(), QuietHoursTests, SettleCallTests (+3 more)

### Community 11 - "ClaudeService"
Cohesion: 0.11
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
Cohesion: 0.06
Nodes (7): MemoryChunkDao, MemoryChunk, MemoryMatch, EmbeddingService, MemoryChunkService, ParseChunksTests, RetrievableQueryTests

### Community 17 - "Harness"
Cohesion: 0.08
Nodes (15): LevelSmoother, Snapshot, State, calibrating, cooldown, idle, onset, speaking (+7 more)

### Community 20 - "settings_controller.py"
Cohesion: 0.11
Nodes (6): get_all_settings(), get_available_models(), get_claude_credits(), ModelSwitchRequest, set_model(), ClaudeCreditsService

### Community 21 - "processes.py"
Cohesion: 0.15
Nodes (16): _all(), await_ready(), check(), _entry(), kill_tree(), _log_paths(), pid_alive(), port_open() (+8 more)

### Community 22 - "process_supervisor.py"
Cohesion: 0.11
Nodes (18): _all(), await_ready(), check(), classify(), _entry(), kill_tree(), _log_paths(), pid_alive() (+10 more)

### Community 23 - "build_service"
Cohesion: 0.12
Nodes (6): build_service(), FakeConversationService, FakeEmbeddingService, FakeMemoryChunkDao, FetchMemoryTests, ProcessConversationsTests

### Community 24 - "MeetingError"
Cohesion: 0.08
Nodes (19): transcribe_segments_serialized(), delete_meeting(), get_active_meeting(), get_meeting(), get_meeting_segments(), list_meetings(), _meeting_error(), meeting_socket() (+11 more)

### Community 25 - "CursorService"
Cohesion: 0.11
Nodes (11): backend_url(), close_current_conversation(), fetch_conversation_info(), fetch_health(), fetch_projects(), fetch_tools(), stream_reply(), CursorService (+3 more)

### Community 28 - "CodingSession"
Cohesion: 0.18
Nodes (3): CodingSessionDao, CodingEvent, CodingSession

### Community 29 - "Update"
Cohesion: 0.05
Nodes (7): UpdateDao, CodingStatus, DeliveryStatus, ReportType, Update, UpdateService, EscapingTests

### Community 30 - "ConversationController"
Cohesion: 0.12
Nodes (6): Capture, ConversationController, .isEnabled, .wakeWatching, Once, NovaSocketing

### Community 31 - "ElevenLabsService"
Cohesion: 0.16
Nodes (5): _describe_failure(), ElevenLabsService, ElevenLabsRequestTests, _env(), ProviderSelectionTests

### Community 33 - "test_auth_service.py"
Cohesion: 0.09
Nodes (4): NovaSessionDao, row_to_session(), NovaSession, RowConversionTests

### Community 35 - "auth_controller.py"
Cohesion: 0.10
Nodes (10): _client_ip(), current_session(), list_sessions(), login(), logout(), logout_all(), AuthNotConfigured, BadCredentials (+2 more)

### Community 37 - "__main__.py"
Cohesion: 0.13
Nodes (7): Config, _flag(), load_env_file(), _configure_logging(), main(), _run(), _task()

### Community 38 - "VisionService"
Cohesion: 0.08
Nodes (7): Vision: "Hey Nova, what do you see?", _in_view_text(), is_image_block(), VisionService, ContentBlocksTests, LookToolTests, phone()

### Community 39 - "test_meeting_service.py"
Cohesion: 0.06
Nodes (9): FakeAgentLoop, FakeChunkDao, FakeClaudeService, FakeConversationDao, FakeEmbeddingService, FakeNotesDao, FakeUpdateService, RecoveryTests (+1 more)

### Community 40 - "DATGlassesCamera"
Cohesion: 0.08
Nodes (8): CameraError, .errorDescription, failed, glassesAudioNotUp, noCamera, notReady, timeout, DATGlassesCamera

### Community 42 - "build_service"
Cohesion: 0.21
Nodes (5): build_service(), CreateTests, FakeProjectDao, FakeUpdateService, soon()

### Community 44 - "Responsibility"
Cohesion: 0.17
Nodes (4): Responsibility, at(), CheckForResponsibilitiesTests, DueTests

### Community 45 - "McpOAuthService"
Cohesion: 0.26
Nodes (3): McpOAuthService, _origin(), _path()

### Community 46 - "make_update"
Cohesion: 0.16
Nodes (5): ConversationResolutionTests, make_update(), OpeningPromptTests, TwiMLTests, form()

### Community 47 - "build_service"
Cohesion: 0.07
Nodes (17): MeetingSegment, build_service(), ChunkingTests, CommitSegmentsTests, DeleteMeetingTests, FakeProjectDao, FinalizeTests, FollowUpTests (+9 more)

### Community 48 - "asr_service.py"
Cohesion: 0.19
Nodes (8): main(), _hotwords(), _load_parakeet(), missing_cuda_libraries(), _nvidia_wheel_dll_dirs(), _platform_default_provider(), _resolve_whisper_device(), _setup_cuda_libraries()

### Community 49 - "call_controller.py"
Cohesion: 0.10
Nodes (15): answer_call(), call_status(), _escape(), mint_relay_token(), _opening_prompt(), relay_socket(), start_turn(), run_after_previous() (+7 more)

### Community 52 - "nova_controller.py"
Cohesion: 0.06
Nodes (16): PromptSourceEnum, chat_stream(), event_source(), get_nova_power(), get_nova_state(), parse_conversation_id(), resolve_chat_request(), sse_event() (+8 more)

### Community 53 - "test_auth_gate.py"
Cohesion: 0.14
Nodes (6): AuthGate, bearer_token(), _header(), is_exempt(), build_app(), ExemptionTests

### Community 54 - "AuthService"
Cohesion: 0.11
Nodes (4): AuthService, _hash_token(), _now(), ConfigurationTests

### Community 56 - "TwilioErrorClassificationTests"
Cohesion: 0.15
Nodes (6): describe_twilio_error(), is_permanent_twilio_error(), SimpleNamespace_Exception, TwilioErrorClassificationTests, reject(), flake()

### Community 58 - "Meeting"
Cohesion: 0.10
Nodes (3): MeetingDao, Meeting, MeetingStatus

### Community 59 - "ConversationLoopStreamTests"
Cohesion: 0.16
Nodes (5): ConversationLoopStreamTests, fake_stream(), fake_stream(), fake_stream(), EventStreamTests

### Community 61 - "SpeechPlayer"
Cohesion: 0.07
Nodes (7): MP3StreamDecoder, PlaybackWatchdog, SpeechPlayer, .isBusy, .now, Stream, PlaybackWatchdogTests

### Community 62 - "EndpointDecisionTests"
Cohesion: 0.10
Nodes (5): endpoint_decision(), _endpoint_scale(), EndpointDecision, silence_budget_ms(), EndpointDecisionTests

### Community 63 - "ImageStore"
Cohesion: 0.13
Nodes (6): capture_failed(), CaptureFailed, ImageStore, VisionImage, GlassesSocketTests, ImageStoreTests

### Community 64 - "FakeCamera"
Cohesion: 0.23
Nodes (4): FakeCamera, FakeVision, settle(), VisionControllerTests

### Community 67 - "test_spoken_reply.py"
Cohesion: 0.16
Nodes (6): _comparable(), is_repeat(), _plain_text(), strip_speak_tags(), IsRepeatTests, StripSpeakTagsTests

### Community 68 - "ClientEvent"
Cohesion: 0.08
Nodes (22): Note, AudioRole, final, progress, status, wake, CapturePurpose, sentry (+14 more)

### Community 71 - "re"
Cohesion: 0.16
Nodes (7): _canonical_wake_text(), has_stop_phrase(), has_wake_phrase(), normalize_wake_text(), split_wake_phrase(), SplitWakePhraseTests, WakePhraseTests

### Community 72 - "McpServer"
Cohesion: 0.20
Nodes (4): McpServer, _b64url(), _now(), _parse_expiry()

### Community 73 - "FakeDao"
Cohesion: 0.10
Nodes (4): GateTestCase, AuthenticateTests, AuthServiceTestCase, FakeDao

### Community 74 - "TwilioService"
Cohesion: 0.09
Nodes (5): main(), report(), TwilioConfigurationError, TwilioService, ConfigurationGuardTests

### Community 76 - "AgentLoop"
Cohesion: 0.04
Nodes (17): AgentLoop, persist(), _env_flag(), ToolService, CountingService, FakeConversationService, FakeToolDao, PrefetchedConversationTests (+9 more)

### Community 77 - "faces_controller.py"
Cohesion: 0.10
Nodes (12): add_sample(), create_person(), delete_person(), _enroll(), list_people(), read_jpeg_body(), upload_image(), DuplicatePerson (+4 more)

### Community 78 - "Any"
Cohesion: 0.25
Nodes (3): _as_int(), _flatten(), _ms_to_iso()

### Community 79 - "transcribe_socket"
Cohesion: 0.18
Nodes (9): parse_image_ids(), _partial_is_due(), send_assistant_text(), _send_locked(), _speculative_asr_enabled(), stream_tts_audio(), transcribe_socket(), send() (+1 more)

### Community 80 - "String"
Cohesion: 0.13
Nodes (13): Phase, idle, listening, off, speaking, thinking, PhotoSlot, GlassesCamera (+5 more)

### Community 81 - "SpokenTrackTests"
Cohesion: 0.23
Nodes (3): FakeToolUseBlock, SpokenTrackTests, fake_stream()

### Community 83 - "FakeMcpServerDao"
Cohesion: 0.17
Nodes (3): build_service(), FakeMcpServerDao, McpServerServiceTests

### Community 86 - "SettingsService"
Cohesion: 0.12
Nodes (3): SettingsService, ModelListTests, _ResetsSharedState

### Community 87 - "Person"
Cohesion: 0.11
Nodes (3): PersonDao, Person, FakePersonDao

### Community 88 - "test_sms.py"
Cohesion: 0.05
Nodes (20): BipConfigurationError, BipRequestError, BipService, _describe_response_error(), is_permanent_bip_error(), normalize_phone_number(), _parse_number_list(), SmsRecipientError (+12 more)

### Community 89 - "ServerEvent"
Cohesion: 0.08
Nodes (21): ServerEvent, audioStreamChunk, audioStreamEnd, audioStreamStart, captureRequest, chunkReceived, done, error (+13 more)

### Community 90 - "StreamedSpeechTests"
Cohesion: 0.27
Nodes (3): stream(), StreamedSpeechTests, fake_stream()

### Community 92 - "test_memory_injection.py"
Cohesion: 0.14
Nodes (10): build_memory_service(), FakeConversationService, FakeEmbeddingService, FakeMemoryChunkDao, FakeMessage, FakeTextBlock, FakeToolDao, match() (+2 more)

### Community 93 - "test_responsibility_service.py"
Cohesion: 0.11
Nodes (5): build_service(), FakeProjectDao, FakeResponsibilityDao, FakeUpdateService, WindowTests

### Community 96 - "pending"
Cohesion: 0.17
Nodes (4): ListAndCancelTests, pending(), RecoverStuckTests, RunDueTests

### Community 97 - "Mac code agent daemon"
Cohesion: 0.16
Nodes (14): Nova code agent (Mac) README, Anthropic API key stripping, Mac dials out design, Per-session git worktree, Known limits (awake Mac, bounded replay, cache cost), launchd install and menu app, Mac code agent daemon, NOVA_CODE_TOKEN shared secret (+6 more)

### Community 101 - "._run_begin"
Cohesion: 0.26
Nodes (5): BeginFlowTests, fake_get(), fake_post(), fake_post(), FakeResponse

### Community 104 - "Keys"
Cohesion: 0.10
Nodes (20): Keys, assistantText, bytes, chunkBase64, client, code, conversationId, count (+12 more)

### Community 105 - "FaceService"
Cohesion: 0.14
Nodes (5): FaceService, face_row(), FaceServiceTests, FacesRoutesTests, unit()

### Community 106 - "Sendable"
Cohesion: 0.15
Nodes (10): Cancellable, EarconPlaying, Handle, MainScheduler, Scheduling, SocketConnectionState, connected, connecting (+2 more)

### Community 107 - "pathlib"
Cohesion: 0.15
Nodes (8): audio_file_bytes(), is_raw_pcm(), _pcm_params(), suffix_for_mime(), transcribe_serialized(), emit_partial_transcript(), run_speculative_transcription(), AudioFileBytesTests

### Community 108 - "GlassesCameraState"
Cohesion: 0.12
Nodes (9): ConversationIdStore, GlassesCameraState, .canCapture, ready, registering, streaming, unavailable, unregistered (+1 more)

### Community 109 - "PreRollBuffer"
Cohesion: 0.20
Nodes (4): PCMFormat, PreRollBuffer, .count, AudioFramingTests

### Community 110 - "test_asr_filters.py"
Cohesion: 0.26
Nodes (4): drop_hallucination(), DropHallucinationTests, _segment(), WhisperSegmentFilterTests

### Community 111 - "FakeDao"
Cohesion: 0.16
Nodes (5): CompleteAndRefreshTests, fake_post(), ConnectorFilteringTests, FakeDao, oauth_server()

### Community 113 - "sessions.py"
Cohesion: 0.19
Nodes (3): _contained(), make_guard(), _is_prose()

### Community 114 - "AppModel"
Cohesion: 0.07
Nodes (17): AppModel, .serverURLString, NovaGlassesApp, .body, RootView, .body, AudioLogView, HomeView (+9 more)

### Community 115 - "meeting_service.py"
Cohesion: 0.10
Nodes (5): PromptEnums, MeetingChunkDao, MeetingNotesDao, MeetingChunk, MeetingNotes

### Community 117 - "host_environment_prompt.py"
Cohesion: 0.31
Nodes (3): host_environment_prompt(), _host_kind(), _machine_line()

### Community 118 - "APIClient"
Cohesion: 0.17
Nodes (7): APIClient, APIError, badResponse, .errorDescription, server, unauthorized, Person

### Community 119 - "Foundation"
Cohesion: 0.08
Nodes (12): AudioToolbox, AVFoundation, Foundation, ImageIO, AudioSessionPolicy, ImagePrep, MWDATCamera, MWDATCore (+4 more)

### Community 120 - "Earcon"
Cohesion: 0.18
Nodes (9): Earcons, Earcon, cancel, done, error, shutter, thinking, waiting (+1 more)

### Community 124 - "main.py"
Cohesion: 0.14
Nodes (7): can_use_tool(), _allowed_origins(), health(), lifespan(), root(), _broadcast(), face_socket()

### Community 125 - "worker.py"
Cohesion: 0.27
Nodes (8): build_jobs(), _recover_stuck_tasks(), _run_check_for_responsibilities(), _run_deliver_pending_updates(), _run_process_conversations(), _run_scheduled_tasks(), run_worker(), ScheduledJob

### Community 126 - "asr-bench.py"
Cohesion: 0.36
Nodes (4): cut_clips(), default_audio(), load(), main()

### Community 128 - "agent_loop.py"
Cohesion: 0.08
Nodes (9): MessageDao, Message, MessageRole, ToolUseStarted, TurnStream, FakeProjectDao, FakeClaudeResponse, FakeClaudeService (+1 more)

### Community 131 - "test_process_supervisor.py"
Cohesion: 0.09
Nodes (5): fetch(), main(), sha256(), ClassificationTests, MirrorTests

### Community 135 - "FakePlayer"
Cohesion: 0.19
Nodes (3): FakePlayer, .isBusy, FakeWake

### Community 136 - "ToolExecutionError"
Cohesion: 0.25
Nodes (3): main(), main(), ToolExecutionError

### Community 139 - ".add"
Cohesion: 0.12
Nodes (6): AudioLog, Entry, AudioRouteManager, Route, .summary, .body

### Community 141 - "run_migrations.py"
Cohesion: 0.16
Nodes (4): main(), migration_files(), _jsonable(), SQLService

### Community 142 - "SpokenProse"
Cohesion: 0.19
Nodes (3): SpokenProse, _said(), SpokenProseTests

### Community 143 - "TTSService"
Cohesion: 0.15
Nodes (4): NovaService, OpenAITTS, _requested_provider(), TTSService

### Community 148 - "._conversation_turn"
Cohesion: 0.14
Nodes (4): deliver(), _clamp(), clamp_spoken(), ClampSpokenTests

### Community 153 - ".completed"
Cohesion: 0.12
Nodes (8): fake_stream(), fake_stream(), fake_stream(), fake_stream(), TurnStreamTests, get_final_message(), fake_stream(), fake_stream()

### Community 154 - ".setUp"
Cohesion: 0.16
Nodes (7): fake_get_response(), FakeConversationService, FakeMessage, FakeTextBlock, FakeToolDao, FakeUpdateService, fake_get_response()

### Community 155 - "WakeDetecting"
Cohesion: 0.13
Nodes (8): WakeDetecting, Build and test (CLI), Code map, How it behaves, Install on your iPhone, NovaGlasses, On-device field checklist, What is verified and what is not

### Community 157 - "worktree.py"
Cohesion: 0.23
Nodes (7): create(), _git(), remove(), resolve_repo(), slugify(), Workspace, WorktreeError

### Community 159 - "mcp_server_controller.py"
Cohesion: 0.18
Nodes (6): _callback_page(), create_mcp_server(), delete_mcp_server(), list_mcp_servers(), mcp_oauth_callback(), update_mcp_server()

### Community 161 - "asyncio"
Cohesion: 0.10
Nodes (13): _authorized(), coding_socket(), close_conversation(), get_conversation(), get_conversation_messages(), _parse_uuid(), _project_payload(), get_project() (+5 more)

### Community 170 - "os"
Cohesion: 0.22
Nodes (5): classify(), _clip(), _resolve_cwd(), run(), _scratch_pair()

### Community 176 - "match"
Cohesion: 0.19
Nodes (4): GalleryPerson, match(), _normalise(), MatchTests

### Community 177 - "VisionRoutesTests"
Cohesion: 0.26
Nodes (3): Identification, FakeFaceService, VisionRoutesTests

### Community 178 - "ConversationControllerTests.swift"
Cohesion: 0.27
Nodes (4): ConversationControllerTests.Rig, FakeEarcons, NovaGlasses, XCTest

### Community 179 - "prepare"
Cohesion: 0.31
Nodes (3): prepare(), jpeg(), PrepareTests

### Community 181 - "AddPersonView"
Cohesion: 0.12
Nodes (7): .api, VisionClient, AddPersonView, .body, FacesView, .body, PhotosUI

### Community 182 - "AuthStore"
Cohesion: 0.28
Nodes (3): AuthStore, .baseQuery, Security

### Community 184 - "protocol.py"
Cohesion: 0.39
Nodes (3): _artifact_for(), encode(), _truncate()

### Community 185 - "CodeServiceTestCase"
Cohesion: 0.14
Nodes (4): CodeServiceTestCase, EditTests, FakeConversationDao, FakeProjectDao

### Community 187 - "XCTestCase"
Cohesion: 0.21
Nodes (3): VisionIntent, AudioSessionPolicyTests, VisionIntentTests

## Ambiguous Edges - Review These
- `TTS conversion enhancer prompt (empty)` → `Voice mode tone guidelines`  [AMBIGUOUS]
  prompting/tts_conversion_enhancer_prompt.txt · relation: conceptually_related_to

## Knowledge Gaps
- **140 isolated node(s):** `UserNotifications`, `.serverURLString`, `.summary`, `AudioToolbox`, `.count` (+135 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1320 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **78 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `TTS conversion enhancer prompt (empty)` and `Voice mode tone guidelines`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `NovaGlasses` connect `WakeDetecting` to `VisionService`?**
  _High betweenness centrality (0.310) - this node is a cross-community bridge._
- **Are the 36 inferred relationships involving `AgentLoop` (e.g. with `PromptEnums` and `PromptSourceEnum`) actually correct?**
  _`AgentLoop` has 36 INFERRED edges - model-reasoned connections that need verification._
- **What connects `UserNotifications`, `.serverURLString`, `.summary` to the rest of the system?**
  _140 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Tool` be split into smaller, more focused modules?**
  _Cohesion score 0.12923076923076923 - nodes in this community are weakly interconnected._
- **Why does `Vision: "Hey Nova, what do you see?"` connect `VisionService` to `WakeDetecting`?**
  _High betweenness centrality (0.310) - this node is a cross-community bridge._
- **Are the 17 inferred relationships involving `Conversation` (e.g. with `_is_stale()` and `ConversationDao`) actually correct?**
  _`Conversation` has 17 INFERRED edges - model-reasoned connections that need verification._