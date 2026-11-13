# Graph Report - nova-backend  (2026-11-13)

## Corpus Check
- 237 files · ~204,694 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: (none) 3, .mdc 1, .pbxproj 1)

## Summary
- 5094 nodes · 11966 edges · 229 communities (139 shown, 90 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 1282 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e7554b68`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- ToolService
- sms_controller.py
- SimpleFinancesService
- text
- TranscribeSocketTests
- test_openai_loop.py
- Rig
- AgentLoopImageTests
- test_background_agent.py
- ._env
- make_update
- ClaudeService
- GithubService
- build_service
- Nova system prompt (persona)
- HomeView
- Harness
- CodingService
- ScheduledTask
- _most_recent_local_midnight_utc
- json
- process_supervisor.py
- build_service
- MeetingError
- CursorService
- MeetingService
- FileOperationTests
- CodingSession
- Update
- ConversationController
- test_tts_service.py
- time
- test_auth_service.py
- LiveReply
- LockoutTests
- .start
- __main__.py
- ProjectDao
- asyncio
- DATGlassesCamera
- Ports.swift
- pending
- ReportType
- Responsibility
- .begin
- make_update
- build_service
- Meeting
- call_controller.py
- McpServerService
- requests
- TurnTimer
- AuthService
- auth_service.py
- Message
- build_service
- FakeMessage
- FakePersonaDao
- ConversationLoopStreamTests
- ReplyTests
- SpeechPlayer
- EndpointDecisionTests
- .look
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
- .durationMs
- SidekickGate
- AuthStore
- fake_stream
- LiveScreenTests
- FakeMcpServerDao
- FakeMeetingDao
- CrudTests
- SettingsService
- Person
- test_sms.py
- ServerEvent
- StreamedSpeechTests
- test_coding_service.py
- test_memory_injection.py
- test_meeting_service.py
- ASRService
- AsrLock
- UpdateService
- Mac code agent daemon
- FakeTaskDao
- ServiceMethodToolConfig
- test_claude_service.py
- ._run_begin
- update_delivery_service.py
- NovaSocket
- Keys
- FaceService
- os
- turn_timer.py
- ConversationIdStore
- .repair_tool_pairing
- DeployService
- McpOAuthService
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
- test_deploy_main.py
- agent_loop.py
- ._to_dict
- FakeDao
- ClassificationTests
- test_glasses_voice.py
- CaptureEngine
- history_compaction.py
- FakeConversationService
- SidekickConnection
- WorkingTreeTests
- AudioRouteManager
- .isOnlyWakePhrase
- IsIdleTests
- SpokenProse
- tts_service.py
- ImageStore
- RelayTokenTests
- SpeechWakeDetector
- MeetingSegment
- clamp_spoken
- TwilioErrorClassificationTests
- SpokenTrackTests
- .iter_sentence_chunks
- GoodbyeTimingTests
- VisionService
- .conversation_loop_events
- EmbeddingService
- test_process_supervisor.py
- FallbackChainTests
- PassSentinelTests
- Rig
- CLAUDE.md
- auth_controller.py
- install.sh
- uninstall.sh
- settings_controller.py
- nova-backend
- worktree.py
- CurrentModelTests
- FakeHttp
- CommandLineService
- DemoService
- CooldownTests
- BipService
- prepare
- .completed
- Entry
- String
- AddPersonView
- PersonaPrompt
- .setUp
- endpointing_service.py
- GlassesSocketTests
- replay_request.py
- .wantsToSee
- SessionManager
- ._conversation_turn
- DeliveryStatus
- MacSessionLifecycleTests
- SentryModeTests
- split_wake_phrase
- FailureSpeechTests
- conversation_controller.py
- InterruptedToolCallTests
- fastapi
- FakeConversationService
- ThinkingPulseTests
- GuardrailTests
- FakeUpdateService
- mcp_server_controller.py
- chat_stream
- Link
- FakeUpdateDao
- AgentLink
- _FakeTable
- shell.py
- VisionClient
- FinishedSessionTowerTests
- protocol.py
- ._persist_message_later
- FallbackTests
- .split_sms_body
- .ensure_fresh
- parse_gate_reply
- .test_a_live_turn_reads_deltas_then_exposes_the_message
- main.py
- ScheduledTaskService
- test_persona_service.py
- ._parse_chunks
- get_nova_state
- WebSocketGateTests
- CodingStatus
- transcribe_utterance
- LoginTests

## God Nodes (most connected - your core abstractions)
1. `AgentLoop` - 121 edges
2. `Conversation` - 89 edges
3. `ConversationController` - 83 edges
4. `ToolService` - 68 edges
5. `build_service()` - 57 edges
6. `MeetingService` - 52 edges
7. `CodingService` - 49 edges
8. `Tool` - 48 edges
9. `Responsibility` - 47 edges
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

## Communities (229 total, 90 thin omitted)

### Community 0 - "ToolService"
Cohesion: 0.09
Nodes (13): main(), main(), main(), main(), main(), migration_files(), list_tools(), ToolDao (+5 more)

### Community 1 - "sms_controller.py"
Cohesion: 0.16
Nodes (8): _authorize(), _handle_inbound(), inbound_sms(), inbound_sms_with_path_token(), _is_stale(), _receive(), resolve_sms_conversation(), _run_sms_turn()

### Community 2 - "SimpleFinancesService"
Cohesion: 0.11
Nodes (6): SimplApiError, SimplConfigurationError, SimpleFinancesService, response(), SimpleFinancesServiceTest, SimplFinancesToolRegistrationTest

### Community 3 - "text"
Cohesion: 0.08
Nodes (9): _jsonable(), SQLService, AuthenticationTests, forward(), make_request(), PathTokenRouteTests, SenderGateTests, go() (+1 more)

### Community 5 - "test_openai_loop.py"
Cohesion: 0.17
Nodes (7): FakeClient, FakeFunctionCall, FakeResponse, FakeResponsesAPI, FakeTool, FakeToolService, OpenAILoopTests

### Community 6 - "Rig"
Cohesion: 0.13
Nodes (6): FakePlayer, .isBusy, FakeWake, Item, ManualScheduler, Rig

### Community 7 - "AgentLoopImageTests"
Cohesion: 0.17
Nodes (5): AgentLoopImageTests, fake_stream(), FakeConversationService, FakeMessage, FakeTextBlock

### Community 8 - "test_background_agent.py"
Cohesion: 0.07
Nodes (12): BackgroundAgentTests, fake_get_response(), FakeConversationService, FakeMessage, FakeProjectDao, FakeTextBlock, FakeToolDao, FakeUpdateService (+4 more)

### Community 9 - "._env"
Cohesion: 0.15
Nodes (3): CartesiaService, CartesiaRequestTests, ProviderSelectionTests

### Community 10 - "make_update"
Cohesion: 0.14
Nodes (11): at(), BadgeOnlyTests, build_service(), CallDeliveryTests, EmailDeliveryTests, make_update(), QuietHoursTests, SettleCallTests (+3 more)

### Community 11 - "ClaudeService"
Cohesion: 0.09
Nodes (5): ClaudeService, _maybe_dump_request(), _maybe_print_prompt(), GenerationKwargsTests, ClaudeServiceMcpKwargsTests

### Community 12 - "GithubService"
Cohesion: 0.15
Nodes (4): GithubService, GithubServiceError, _FakeResponse, GithubServiceTests

### Community 13 - "build_service"
Cohesion: 0.12
Nodes (7): build_service(), CreateUpdateTests, FakeConversationDao, FakeProjectDao, make_update(), ReportTypeTests, ViewingTests

### Community 14 - "Nova system prompt (persona)"
Cohesion: 0.07
Nodes (28): Hosting Nova off the home network, Backend environment variables, Cloudflare Tunnel (nova-tower, cloudflared), Firebase Hosting frontend (nova-voice-nd.web.app), Infobip SMS integration (/sms/inbound), Failed-login lockout policy, Mac coding agent (/ws/coding), MCP OAuth callback (+20 more)

### Community 15 - "HomeView"
Cohesion: 0.11
Nodes (13): NovaGlassesApp, .body, RootView, AudioLogView, HomeView, .cameraText, .connectionText, .controller (+5 more)

### Community 17 - "Harness"
Cohesion: 0.08
Nodes (15): LevelSmoother, Snapshot, State, calibrating, cooldown, idle, onset, speaking (+7 more)

### Community 19 - "ScheduledTask"
Cohesion: 0.14
Nodes (3): ScheduledTaskDao, ScheduledTask, TaskStatus

### Community 20 - "_most_recent_local_midnight_utc"
Cohesion: 0.11
Nodes (6): _most_recent_local_midnight_utc(), IsPastRolloverTests, build_service(), CheckForStaleConversationsTests, FakeConversationDao, MostRecentLocalMidnightUtcTests

### Community 21 - "json"
Cohesion: 0.16
Nodes (16): _all(), await_ready(), check(), _entry(), kill_tree(), _log_paths(), pid_alive(), port_open() (+8 more)

### Community 22 - "process_supervisor.py"
Cohesion: 0.11
Nodes (18): _all(), await_ready(), check(), classify(), _entry(), kill_tree(), _log_paths(), pid_alive() (+10 more)

### Community 23 - "build_service"
Cohesion: 0.07
Nodes (11): build_service(), FakeClaudeService, FakeConversationService, FakeEmbeddingService, FakeMemoryChunkDao, FetchMemoryTests, ProcessConversationsTests, boom() (+3 more)

### Community 24 - "MeetingError"
Cohesion: 0.09
Nodes (19): transcribe_segments_serialized(), delete_meeting(), get_active_meeting(), get_meeting(), get_meeting_segments(), list_meetings(), _meeting_error(), meeting_socket() (+11 more)

### Community 25 - "CursorService"
Cohesion: 0.17
Nodes (4): CursorService, CursorServiceError, CursorServiceTests, _FakeResponse

### Community 27 - "FileOperationTests"
Cohesion: 0.06
Nodes (7): CodeServiceTestCase, EditTests, FakeConversationDao, FakeProjectDao, FileOperationTests, PathContainmentTests, ProjectResolutionTests

### Community 28 - "CodingSession"
Cohesion: 0.17
Nodes (3): CodingSessionDao, CodingEvent, CodingSession

### Community 29 - "Update"
Cohesion: 0.09
Nodes (4): Update, EmailService, _env_int(), UpdateDeliveryService

### Community 30 - "ConversationController"
Cohesion: 0.11
Nodes (8): Capture, ConversationController, .idleMessage, .isEnabled, .isWorking, .wakeWatching, Once, Sentry mode

### Community 31 - "test_tts_service.py"
Cohesion: 0.13
Nodes (5): _describe_failure(), _describe_failure(), ElevenLabsService, ElevenLabsRequestTests, _full_chain_env()

### Community 32 - "time"
Cohesion: 0.09
Nodes (18): build_logger(), check_health_once(), current_commit(), DeployConfig, DeployError, DeployRunner, find_pid_on_port(), find_worker_pid() (+10 more)

### Community 33 - "test_auth_service.py"
Cohesion: 0.09
Nodes (4): NovaSessionDao, row_to_session(), NovaSession, RowConversionTests

### Community 37 - "__main__.py"
Cohesion: 0.15
Nodes (7): Config, _flag(), load_env_file(), _configure_logging(), main(), _run(), _task()

### Community 38 - "ProjectDao"
Cohesion: 0.08
Nodes (3): ProjectDao, CodeService, ProjectService

### Community 39 - "asyncio"
Cohesion: 0.06
Nodes (26): logout_all(), adopt_claude_thread(), _authorized(), coding_socket(), coding_status(), get_coding_session(), list_claude_threads(), list_coding_sessions() (+18 more)

### Community 40 - "DATGlassesCamera"
Cohesion: 0.07
Nodes (15): CameraError, .errorDescription, failed, glassesAudioNotUp, noCamera, notReady, timeout, DATGlassesCamera (+7 more)

### Community 41 - "Ports.swift"
Cohesion: 0.11
Nodes (11): Cancellable, Handle, MainScheduler, Scheduling, WakeDetecting, Build and test (CLI), Code map, How it behaves (+3 more)

### Community 42 - "pending"
Cohesion: 0.22
Nodes (4): pending(), RecoverStuckTests, RunDueTests, RunTests

### Community 43 - "ReportType"
Cohesion: 0.09
Nodes (3): ResponsibilityDao, ReportType, ResponsibilityService

### Community 44 - "Responsibility"
Cohesion: 0.06
Nodes (12): Responsibility, at(), build_service(), CheckForResponsibilitiesTests, CreateScheduleRequirementTests, DueTests, FakeProjectDao, FakeResponsibilityDao (+4 more)

### Community 45 - ".begin"
Cohesion: 0.20
Nodes (3): _b64url(), _origin(), _path()

### Community 46 - "make_update"
Cohesion: 0.16
Nodes (5): ConversationResolutionTests, make_update(), OpeningPromptTests, TwiMLTests, form()

### Community 47 - "build_service"
Cohesion: 0.09
Nodes (12): build_service(), ChunkingTests, CommitSegmentsTests, DeleteMeetingTests, FakeProjectDao, FollowUpTests, explode(), recording_meeting() (+4 more)

### Community 48 - "Meeting"
Cohesion: 0.09
Nodes (3): MeetingDao, Meeting, MeetingStatus

### Community 49 - "call_controller.py"
Cohesion: 0.09
Nodes (16): answer_call(), call_status(), _escape(), mint_relay_token(), _opening_prompt(), relay_socket(), start_turn(), run_after_previous() (+8 more)

### Community 51 - "requests"
Cohesion: 0.27
Nodes (7): backend_url(), close_current_conversation(), fetch_conversation_info(), fetch_health(), fetch_projects(), fetch_tools(), stream_reply()

### Community 52 - "TurnTimer"
Cohesion: 0.18
Nodes (4): _emit(), mark(), TurnTimer, TurnTimerTests

### Community 53 - "AuthService"
Cohesion: 0.09
Nodes (8): AuthGate, bearer_token(), _header(), is_exempt(), AuthService, build_app(), ExemptionTests, SidekickAuthTests

### Community 54 - "auth_service.py"
Cohesion: 0.15
Nodes (3): _hash_token(), _now(), ConfigurationTests

### Community 56 - "build_service"
Cohesion: 0.15
Nodes (6): build_service(), CreateTests, FakeProjectDao, FakeUpdateService, ListAndCancelTests, soon()

### Community 57 - "FakeMessage"
Cohesion: 0.21
Nodes (4): FakeMessage, FakeTextBlock, StatusTextTests, ToolTurnSpeechTests

### Community 58 - "FakePersonaDao"
Cohesion: 0.14
Nodes (7): build_service(), CachingTests, FakePersonaDao, LoadingTests, seed_row(), ToolFacingWrapperTests, VersioningAndRollbackTests

### Community 59 - "ConversationLoopStreamTests"
Cohesion: 0.13
Nodes (4): ConversationLoopStreamTests, fake_stream(), fake_stream(), EventStreamTests

### Community 61 - "SpeechPlayer"
Cohesion: 0.07
Nodes (7): MP3StreamDecoder, PlaybackWatchdog, SpeechPlayer, .isBusy, .now, Stream, PlaybackWatchdogTests

### Community 63 - ".look"
Cohesion: 0.10
Nodes (13): Vision: "Hey Nova, what do you see?", Client → server, Connecting, Deviations from the brief and additions, Interjections, Prompt and tools, Server behaviour, Server → client (+5 more)

### Community 64 - "FakeCamera"
Cohesion: 0.21
Nodes (4): FakeCamera, FakeVision, settle(), VisionControllerTests

### Community 67 - "test_spoken_reply.py"
Cohesion: 0.16
Nodes (6): _comparable(), is_repeat(), _plain_text(), strip_speak_tags(), IsRepeatTests, StripSpeakTagsTests

### Community 68 - "ClientEvent"
Cohesion: 0.06
Nodes (31): SocketConnectionState, connected, connecting, disconnected, unauthorized, AudioRole, final, progress (+23 more)

### Community 70 - "Conversation"
Cohesion: 0.06
Nodes (6): ConversationDao, Conversation, ConversationClosedError, ConversationService, MemoryChunkService, ThreadResolutionTests

### Community 71 - "nova_controller.py"
Cohesion: 0.13
Nodes (15): _canonical_wake_text(), has_stop_phrase(), normalize_wake_text(), parse_conversation_id(), parse_image_ids(), _partial_is_due(), resolve_chat_request(), send_assistant_text() (+7 more)

### Community 74 - "TwilioService"
Cohesion: 0.09
Nodes (5): main(), report(), TwilioConfigurationError, TwilioService, ConfigurationGuardTests

### Community 76 - "AgentLoop"
Cohesion: 0.05
Nodes (5): AgentLoop, _env_flag(), _PassHold, GlassesPromptSourceTests, SanitizeMcpHistoryTests

### Community 77 - "faces_controller.py"
Cohesion: 0.10
Nodes (12): add_sample(), create_person(), delete_person(), _enroll(), list_people(), read_jpeg_body(), upload_image(), DuplicatePerson (+4 more)

### Community 78 - ".durationMs"
Cohesion: 0.20
Nodes (4): PCMFormat, PreRollBuffer, .count, AudioFramingTests

### Community 80 - "AuthStore"
Cohesion: 0.24
Nodes (3): AuthStore, .baseQuery, Security

### Community 81 - "fake_stream"
Cohesion: 0.14
Nodes (5): fake_stream(), fake_stream(), fake_stream(), fake_stream(), _FakeBadRequestError

### Community 83 - "FakeMcpServerDao"
Cohesion: 0.17
Nodes (3): build_service(), FakeMcpServerDao, McpServerServiceTests

### Community 86 - "SettingsService"
Cohesion: 0.11
Nodes (3): SettingsService, ModelListTests, _ResetsSharedState

### Community 87 - "Person"
Cohesion: 0.11
Nodes (3): PersonDao, Person, FakePersonDao

### Community 88 - "test_sms.py"
Cohesion: 0.14
Nodes (6): BipConfigurationError, BipRequestError, is_permanent_bip_error(), normalize_phone_number(), SmsRecipientError, NormalizationTests

### Community 89 - "ServerEvent"
Cohesion: 0.06
Nodes (26): ServerEvent, audioStreamChunk, audioStreamEnd, audioStreamStart, captureRequest, chunkReceived, done, error (+18 more)

### Community 90 - "StreamedSpeechTests"
Cohesion: 0.27
Nodes (3): stream(), StreamedSpeechTests, fake_stream()

### Community 92 - "test_memory_injection.py"
Cohesion: 0.13
Nodes (10): build_memory_service(), FakeConversationService, FakeEmbeddingService, FakeMemoryChunkDao, FakeMessage, FakeTextBlock, FakeToolDao, match() (+2 more)

### Community 93 - "test_meeting_service.py"
Cohesion: 0.06
Nodes (9): FakeAgentLoop, FakeChunkDao, FakeClaudeService, FakeConversationDao, FakeEmbeddingService, FakeNotesDao, FakeUpdateService, RecoveryTests (+1 more)

### Community 94 - "ASRService"
Cohesion: 0.05
Nodes (21): host_environment_prompt(), _host_kind(), _machine_line(), cut_clips(), default_audio(), load(), main(), main() (+13 more)

### Community 97 - "Mac code agent daemon"
Cohesion: 0.16
Nodes (14): Nova code agent (Mac) README, Anthropic API key stripping, Mac dials out design, Per-session git worktree, Known limits (awake Mac, bounded replay, cache cost), launchd install and menu app, Mac code agent daemon, NOVA_CODE_TOKEN shared secret (+6 more)

### Community 100 - "test_claude_service.py"
Cohesion: 0.14
Nodes (5): _drain(), _FakeMessage, _FakeStream, _FakeUsage, TurnStreamUsageMarkTests

### Community 101 - "._run_begin"
Cohesion: 0.24
Nodes (6): BeginFlowTests, fake_get(), fake_post(), fake_post(), fake_post(), FakeResponse

### Community 104 - "Keys"
Cohesion: 0.08
Nodes (24): Keys, assistantText, bytes, chunkBase64, client, code, conversationId, count (+16 more)

### Community 105 - "FaceService"
Cohesion: 0.11
Nodes (5): FaceService, _normalise(), face_row(), FaceServiceTests, FacesRoutesTests

### Community 106 - "os"
Cohesion: 0.09
Nodes (7): MemoryChunkDao, MemoryChunk, MemoryMatch, MessageRole, Project, FakeClaudeResponse, FakeTextBlock

### Community 107 - "turn_timer.py"
Cohesion: 0.15
Nodes (4): _build_file_logger(), _default_log_path(), _timing_enabled(), HostEnvironmentPromptTests

### Community 108 - "ConversationIdStore"
Cohesion: 0.17
Nodes (5): ConversationIdStore, VoiceMode, conversation, sentry, VoiceModeStore

### Community 110 - "DeployService"
Cohesion: 0.12
Nodes (4): DeployService, HealthTimeoutTests, CheckDeployStatusTests, DeployMainTests

### Community 111 - "McpOAuthService"
Cohesion: 0.22
Nodes (5): McpOAuthService, CompleteAndRefreshTests, ConnectorFilteringTests, FakeDao, oauth_server()

### Community 113 - "sessions.py"
Cohesion: 0.13
Nodes (7): _contained(), make_guard(), can_use_tool(), _flatten(), _is_prose(), health(), root()

### Community 114 - "AppModel"
Cohesion: 0.13
Nodes (6): AppModel, .serverURLString, .body, .body, LoginView, .body

### Community 115 - "meeting_service.py"
Cohesion: 0.09
Nodes (5): BaseDao, MeetingChunkDao, MeetingNotesDao, MeetingChunk, MeetingNotes

### Community 117 - "match"
Cohesion: 0.35
Nodes (4): GalleryPerson, match(), MatchTests, unit()

### Community 118 - "APIClient"
Cohesion: 0.16
Nodes (7): APIClient, APIError, badResponse, .errorDescription, server, unauthorized, Person

### Community 119 - "Foundation"
Cohesion: 0.09
Nodes (12): AudioToolbox, AVFoundation, Foundation, ImageIO, AudioSessionPolicy, ImagePrep, MWDATCamera, MWDATCore (+4 more)

### Community 120 - "Earcon"
Cohesion: 0.12
Nodes (15): Earcons, Note, Earcon, cancel, done, error, shutter, sidekickCue (+7 more)

### Community 121 - "SidekickSocketTests"
Cohesion: 0.15
Nodes (3): GateDecision, SidekickService, SidekickSocketTests

### Community 125 - "worker.py"
Cohesion: 0.16
Nodes (10): BuildJobsTests, build_jobs(), _recover_stuck_tasks(), _run_check_for_responsibilities(), _run_check_for_stale_conversations(), _run_deliver_pending_updates(), _run_process_conversations(), _run_scheduled_tasks() (+2 more)

### Community 126 - "SidekickController"
Cohesion: 0.13
Nodes (6): EarconPlaying, GlassesCamera, NovaSocketing, SpeechPlaying, VisionUploading, SidekickController

### Community 127 - "test_deploy_main.py"
Cohesion: 0.11
Nodes (7): DryRunTests, FailingTestsAbortTests, HappyPathTests, RollbackPathTests, _runner(), _silent_logger(), StopPidIsNeverATreeKillTests

### Community 128 - "agent_loop.py"
Cohesion: 0.06
Nodes (15): PromptSourceEnum, is_sidekick_pass(), strip_expects_reply(), _strip_expects_reply_events(), ToolUseStarted, TurnStream, has_be_quiet_phrase(), _normalize() (+7 more)

### Community 130 - "FakeDao"
Cohesion: 0.10
Nodes (4): GateTestCase, AuthenticateTests, AuthServiceTestCase, FakeDao

### Community 132 - "test_glasses_voice.py"
Cohesion: 0.15
Nodes (8): audio_file_bytes(), is_raw_pcm(), _pcm_params(), suffix_for_mime(), transcribe_serialized(), emit_partial_transcript(), run_speculative_transcription(), AudioFileBytesTests

### Community 135 - "history_compaction.py"
Cohesion: 0.20
Nodes (15): _block_chars(), cap_messages(), clear_old_tool_results(), _clearable_blocks(), compact_history(), _env_int(), _is_plain_user_turn(), _history() (+7 more)

### Community 136 - "FakeConversationService"
Cohesion: 0.12
Nodes (4): FakeConversationService, FakeToolDao, GlassesCannotRecordMeetingsTests, get_all()

### Community 137 - "SidekickConnection"
Cohesion: 0.17
Nodes (3): Utterances, sidekick_socket(), SidekickConnection

### Community 139 - "AudioRouteManager"
Cohesion: 0.22
Nodes (3): AudioRouteManager, Route, .summary

### Community 142 - "SpokenProse"
Cohesion: 0.19
Nodes (3): SpokenProse, _said(), SpokenProseTests

### Community 143 - "tts_service.py"
Cohesion: 0.10
Nodes (9): NovaService, _build_provider(), _ChainedProvider, OpenAITTS, _provider_cooldown_seconds(), _requested_provider(), TTSService, _cartesia() (+1 more)

### Community 144 - "ImageStore"
Cohesion: 0.16
Nodes (4): ImageStore, VisionImage, ContentBlocksTests, ImageStoreTests

### Community 147 - "MeetingSegment"
Cohesion: 0.15
Nodes (5): MeetingSegment, FinalizeTests, NotesTests, NotesUseNoToolsTests, TranscriptTests

### Community 148 - "clamp_spoken"
Cohesion: 0.29
Nodes (3): _clamp(), clamp_spoken(), ClampSpokenTests

### Community 149 - "TwilioErrorClassificationTests"
Cohesion: 0.15
Nodes (6): describe_twilio_error(), is_permanent_twilio_error(), SimpleNamespace_Exception, TwilioErrorClassificationTests, reject(), flake()

### Community 154 - ".conversation_loop_events"
Cohesion: 0.13
Nodes (8): CountingService, PrefetchedConversationTests, fake_stream(), fake_stream(), fake_stream(), fake_stream(), FakeBlock, FakeMessage

### Community 156 - "test_process_supervisor.py"
Cohesion: 0.13
Nodes (4): fetch(), main(), sha256(), MirrorTests

### Community 158 - "PassSentinelTests"
Cohesion: 0.13
Nodes (9): _agent_loop(), FakeConversationService, FakeMessage, FakeTextBlock, FakeToolDao, FakeToolUseBlock, _live(), fake_stream() (+1 more)

### Community 159 - "Rig"
Cohesion: 0.18
Nodes (3): Rig, SidekickControllerTests, SidekickEventCodingTests

### Community 161 - "auth_controller.py"
Cohesion: 0.15
Nodes (8): _client_ip(), current_session(), list_sessions(), login(), logout(), AuthNotConfigured, BadCredentials, LockedOut

### Community 165 - "settings_controller.py"
Cohesion: 0.11
Nodes (6): get_all_settings(), get_available_models(), get_claude_credits(), ModelSwitchRequest, set_model(), ClaudeCreditsService

### Community 170 - "worktree.py"
Cohesion: 0.23
Nodes (7): create(), _git(), remove(), resolve_repo(), slugify(), Workspace, WorktreeError

### Community 172 - "FakeHttp"
Cohesion: 0.16
Nodes (6): build_service(), FakeHttp, FakeResponse, InfobipRequestTests, RecipientAllowlistTests, SendSmsTests

### Community 173 - "CommandLineService"
Cohesion: 0.07
Nodes (3): CommandLineService, BackgroundTests, ForegroundTests

### Community 175 - "CooldownTests"
Cohesion: 0.18
Nodes (3): CooldownTests, refused(), _mock_chain()

### Community 176 - "BipService"
Cohesion: 0.11
Nodes (6): BipService, _describe_response_error(), _parse_number_list(), basic(), InboundSecretTests, SenderAllowlistTests

### Community 177 - "prepare"
Cohesion: 0.13
Nodes (7): Identification, prepare(), FakeFaceService, jpeg(), phone(), PrepareTests, VisionRoutesTests

### Community 178 - ".completed"
Cohesion: 0.12
Nodes (8): fake_stream(), fake_stream(), fake_stream(), fake_stream(), fake_stream(), TurnStreamTests, get_final_message(), fake_stream()

### Community 179 - "Entry"
Cohesion: 0.36
Nodes (3): AudioLog, Entry, .body

### Community 180 - "String"
Cohesion: 0.16
Nodes (12): Phase, idle, listening, off, sentryBlocked, speaking, thinking, PhotoSlot (+4 more)

### Community 181 - "AddPersonView"
Cohesion: 0.17
Nodes (6): .api, AddPersonView, .body, FacesView, .body, PhotosUI

### Community 183 - ".setUp"
Cohesion: 0.12
Nodes (4): DirectTurnCounterTests, fake_transcribe(), FakeGate, FakeSidekickLoop

### Community 184 - "endpointing_service.py"
Cohesion: 0.17
Nodes (4): endpoint_decision(), _endpoint_scale(), EndpointDecision, silence_budget_ms()

### Community 186 - "replay_request.py"
Cohesion: 0.20
Nodes (5): main(), one_call(), main(), one_call(), variants()

### Community 188 - "SessionManager"
Cohesion: 0.27
Nodes (3): _as_int(), _ms_to_iso(), SessionManager

### Community 189 - "._conversation_turn"
Cohesion: 0.15
Nodes (3): deliver(), mark_first_speech(), _memory_block_budget_seconds()

### Community 192 - "SentryModeTests"
Cohesion: 0.06
Nodes (9): AudioSessionPolicyTests, ConversationControllerTests.Rig, SentryModeTests, AmbientForwardingTests, WakePhraseAloneTests, WakeStraightToListeningTests, What is verified and what is not, NovaGlasses (+1 more)

### Community 193 - "split_wake_phrase"
Cohesion: 0.23
Nodes (4): has_wake_phrase(), split_wake_phrase(), SplitWakePhraseTests, WakePhraseTests

### Community 195 - "conversation_controller.py"
Cohesion: 0.27
Nodes (5): close_conversation(), get_conversation(), get_conversation_messages(), _parse_uuid(), _project_payload()

### Community 196 - "InterruptedToolCallTests"
Cohesion: 0.26
Nodes (3): FakeToolUseBlock, InterruptedToolCallTests, _call()

### Community 198 - "FakeConversationService"
Cohesion: 0.22
Nodes (3): FakeConversationService, FakeMcpService, FakeToolDao

### Community 202 - "mcp_server_controller.py"
Cohesion: 0.31
Nodes (3): _callback_page(), list_mcp_servers(), mcp_oauth_callback()

### Community 203 - "chat_stream"
Cohesion: 0.25
Nodes (4): chat_stream(), event_source(), sse_event(), get_final_message()

### Community 207 - "_FakeTable"
Cohesion: 0.13
Nodes (4): CheckForStaleConversationsLoopTests, _FakeResponse, _FakeSupabaseClient, _FakeTable

### Community 208 - "shell.py"
Cohesion: 0.27
Nodes (5): classify(), _clip(), _resolve_cwd(), run(), _scratch_pair()

### Community 212 - "protocol.py"
Cohesion: 0.39
Nodes (3): _artifact_for(), encode(), _truncate()

### Community 220 - "main.py"
Cohesion: 0.18
Nodes (4): _allowed_origins(), lifespan(), _broadcast(), face_socket()

## Ambiguous Edges - Review These
- `TTS conversion enhancer prompt (empty)` → `Voice mode tone guidelines`  [AMBIGUOUS]
  prompting/tts_conversion_enhancer_prompt.txt · relation: conceptually_related_to

## Knowledge Gaps
- **165 isolated node(s):** `UserNotifications`, `.serverURLString`, `.summary`, `AudioToolbox`, `.count` (+160 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1612 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **90 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `TTS conversion enhancer prompt (empty)` and `Voice mode tone guidelines`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `NovaGlasses` connect `Ports.swift` to `SentryModeTests`, `ConversationController`, `.look`?**
  _High betweenness centrality (0.310) - this node is a cross-community bridge._
- **Are the 43 inferred relationships involving `AgentLoop` (e.g. with `Server behaviour` and `PromptEnums`) actually correct?**
  _`AgentLoop` has 43 INFERRED edges - model-reasoned connections that need verification._
- **What connects `UserNotifications`, `.serverURLString`, `.summary` to the rest of the system?**
  _165 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `ToolService` be split into smaller, more focused modules?**
  _Cohesion score 0.08548168249660787 - nodes in this community are weakly interconnected._
- **Why does `Vision: "Hey Nova, what do you see?"` connect `.look` to `Ports.swift`?**
  _High betweenness centrality (0.310) - this node is a cross-community bridge._
- **Are the 21 inferred relationships involving `Conversation` (e.g. with `_is_stale()` and `ConversationDao`) actually correct?**
  _`Conversation` has 21 INFERRED edges - model-reasoned connections that need verification._