# Graph Report - agent-a4463a2fe37416425  (2026-11-13)

## Corpus Check
- 238 files · ~209,789 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 12 file(s) not represented in the graph (top: (none) 4, .mdc 1, .pbxproj 1)

## Summary
- 5195 nodes · 12200 edges · 236 communities (130 shown, 106 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 1289 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `191b1955`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Tool
- normalize_phone_number
- SimpleFinancesService
- text
- TranscribeSocketTests
- test_openai_loop.py
- ServerEvent
- AgentLoopImageTests
- .run_agent
- ._env
- make_update
- ClaudeService
- GithubService
- build_service
- Nova system prompt (persona)
- prepare
- argparse
- Harness
- CodingService
- ScheduledTaskService
- _most_recent_local_midnight_utc
- test_meeting_service.py
- json
- build_service
- MeetingError
- CursorService
- MeetingService
- FileOperationTests
- CodingSession
- ConversationController
- .__init__
- Path
- test_auth_service.py
- LiveReply
- auth_service.py
- SessionManager
- __main__.py
- Project
- asyncio
- DATGlassesCamera
- Handle
- ConversationDao
- ResponsibilityService
- Responsibility
- McpOAuthService
- make_update
- recording_meeting
- post
- call_controller.py
- McpServerService
- ToolService
- TurnTimer
- VisionService
- AuthService
- run_migrations.py
- build_service
- FakeTextBlock
- FakePersonaDao
- ConversationLoopStreamTests
- ReplyTests
- SpeechPlayer
- EndpointDecisionTests
- .look
- FakeCamera
- ConversationControllerTests
- ._artifact_for_tool
- test_background_agent.py
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
- parse_gate_reply
- CameraError
- fake_stream
- LiveScreenTests
- FakeMcpServerDao
- FakeMeetingDao
- CrudTests
- ModelListTests
- Person
- test_sms.py
- test_responsibility_service.py
- StreamedSpeechTests
- test_coding_service.py
- build_memory_service
- meeting_service.py
- ASRService
- AsrLock
- UpdateService
- Mac code agent daemon
- test_spoken_reply.py
- SpokenProse
- MeetingSegment
- ._run_begin
- BipService
- NovaSocket
- Keys
- FaceService
- model/__init__.py
- CompletionNotificationTests
- build_service
- .repair_tool_pairing
- DeployService
- FakeDao
- .run_turn
- make_guard
- AppModel
- asr-bench.py
- FakeMessage
- .create_person
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
- FakeConversationService
- ._to_dict
- FakeDao
- ClassificationTests
- build_app
- CaptureEngine
- AuthenticateTests
- history_compaction.py
- FakeResponsibilityDao
- SidekickConnection
- WorkingTreeTests
- .add
- .isOnlyWakePhrase
- NovaGlasses
- CreateScheduleRequirementTests
- PerformTests
- ImageStore
- RelayTokenTests
- sessions.py
- ToolExecutionError
- EventCodingTests
- FallbackChainTests
- SpokenTrackTests
- .iter_sentence_chunks
- LookToolTests
- .conversation_loop_events
- ._split_transcript
- fetch_face_models.py
- FakeResponse
- PassSentinelTests
- deploy_main.py
- CLAUDE.md
- ._run_agent_loop
- install.sh
- uninstall.sh
- ClaudeCreditsService
- nova-backend
- worktree.py
- SettingsService
- FakeHttp
- CommandLineService
- tool_service.py
- dict
- VisionRoutesTests
- SpeechWakeDetector
- SentryModeTests
- ._spoken_track
- AddPersonView
- PersonaPrompt
- .setUp
- DeployRunner
- GlassesSocketTests
- os
- .wantsToSee
- FailureSpeechTests
- sidekick_service.py
- HostEnvironmentPromptTests
- MacSessionLifecycleTests
- XCTestCase
- ElevenLabsService
- conversation_controller.py
- InterruptedToolCallTests
- CooldownTests
- speech_summary
- ThinkingPulseTests
- GuardrailTests
- .identify
- Any
- CurrentModelTests
- Link
- match
- AgentLink
- _FakeTable
- TTSService
- VisionClient
- ProviderSelectionTests
- FinishedSessionTowerTests
- protocol.py
- FallbackTests
- .split_sms_body
- meeting_socket
- FakePersonDao
- _PassHold
- test_glasses_voice.py
- SidekickService
- test_persona_service.py
- WorktreeCollisionTests
- .test_a_live_turn_reads_deltas_then_exposes_the_message
- MirrorTests
- FakeConversationService
- .is_retrievable_query
- GoodbyeTimingTests
- LockoutTests
- StopPidIsNeverATreeKillTests
- FakeChunkDao
- CaptureFailed
- _describe_failure
- TranscribeUtteranceTests

## God Nodes (most connected - your core abstractions)
1. `AgentLoop` - 128 edges
2. `Conversation` - 89 edges
3. `ConversationController` - 83 edges
4. `ToolService` - 68 edges
5. `build_service()` - 57 edges
6. `CodingService` - 52 edges
7. `MeetingService` - 52 edges
8. `Tool` - 48 edges
9. `Responsibility` - 47 edges
10. `UpdateService` - 46 edges

## Surprising Connections (you probably didn't know these)
- `Server → client` --references--> `stream_tts_audio()`  [INFERRED]
  SIDEKICK_PROTOCOL.md → src/controller/nova_controller.py
- `Server behaviour` --references--> `AgentLoop`  [INFERRED]
  SIDEKICK_PROTOCOL.md → src/harness/agent_loop.py
- `Server behaviour` --references--> `ClaudeService`  [INFERRED]
  SIDEKICK_PROTOCOL.md → src/service/claude_service.py
- `Interjections` --references--> `text()`  [INFERRED]
  SIDEKICK_PROTOCOL.md → tests/test_sms_controller.py
- `Code map` --references--> `WakeDetecting`  [INFERRED]
  ios/NovaGlasses/README.md → ios/NovaGlasses/NovaGlasses/Conversation/Ports.swift

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Remote access path: Firebase frontend to Cloudflare Tunnel to tower API** — docs_hosting_firebase_hosting, docs_hosting_cloudflare_tunnel, docs_hosting_tower_api [EXTRACTED 0.95]
- **Mac agent core design principles** — mac_agent_readme_dial_out, mac_agent_readme_sessions_as_threads, mac_agent_readme_git_worktree [EXTRACTED 1.00]
- **Persisted-action safety rules across foreground and background agents** — prompting_nova_persona_prompt_confirm_persisted_actions, prompting_nova_persona_prompt_clarify_before_executing, prompting_background_agent_prompt_no_outward_actions [INFERRED 0.85]

## Communities (236 total, 106 thin omitted)

### Community 0 - "Tool"
Cohesion: 0.18
Nodes (4): ToolDao, Tool, FakeToolDao, ToolServiceTests

### Community 1 - "normalize_phone_number"
Cohesion: 0.25
Nodes (4): _handle_inbound(), normalize_phone_number(), SmsRecipientError, NormalizationTests

### Community 2 - "SimpleFinancesService"
Cohesion: 0.11
Nodes (6): SimplApiError, SimplConfigurationError, SimpleFinancesService, response(), SimpleFinancesServiceTest, SimplFinancesToolRegistrationTest

### Community 3 - "text"
Cohesion: 0.11
Nodes (8): ToolUseStarted, AuthenticationTests, forward(), make_request(), PathTokenRouteTests, SenderGateTests, go(), text()

### Community 5 - "test_openai_loop.py"
Cohesion: 0.16
Nodes (7): FakeClient, FakeFunctionCall, FakeResponse, FakeResponsesAPI, FakeTool, FakeToolService, OpenAILoopTests

### Community 6 - "ServerEvent"
Cohesion: 0.06
Nodes (26): ServerEvent, audioStreamChunk, audioStreamEnd, audioStreamStart, captureRequest, chunkReceived, done, error (+18 more)

### Community 7 - "AgentLoopImageTests"
Cohesion: 0.23
Nodes (4): AgentLoopImageTests, FakeMessage, FakeTextBlock, FakeToolUseBlock

### Community 8 - ".run_agent"
Cohesion: 0.10
Nodes (3): BackgroundAgentTests, ReportTypeTests, ResponsibilityRunToolRestrictionTests

### Community 10 - "make_update"
Cohesion: 0.06
Nodes (18): describe_twilio_error(), is_permanent_twilio_error(), at(), BadgeOnlyTests, build_service(), CallDeliveryTests, EmailDeliveryTests, FakeUpdateService (+10 more)

### Community 11 - "ClaudeService"
Cohesion: 0.08
Nodes (6): ModelSwitchRequest, set_model(), ClaudeService, _maybe_print_prompt(), GenerationKwargsTests, ClaudeServiceMcpKwargsTests

### Community 12 - "GithubService"
Cohesion: 0.15
Nodes (4): GithubService, GithubServiceError, _FakeResponse, GithubServiceTests

### Community 13 - "build_service"
Cohesion: 0.07
Nodes (9): build_service(), CreateUpdateTests, FakeConversationDao, FakeProjectDao, FakeUpdateDao, make_update(), NotificationQueueFieldsTests, ReportTypeTests (+1 more)

### Community 14 - "Nova system prompt (persona)"
Cohesion: 0.07
Nodes (28): Hosting Nova off the home network, Backend environment variables, Cloudflare Tunnel (nova-tower, cloudflared), Firebase Hosting frontend (nova-voice-nd.web.app), Infobip SMS integration (/sms/inbound), Failed-login lockout policy, Mac coding agent (/ws/coding), MCP OAuth callback (+20 more)

### Community 15 - "prepare"
Cohesion: 0.31
Nodes (3): prepare(), jpeg(), PrepareTests

### Community 16 - "argparse"
Cohesion: 0.23
Nodes (4): main(), main(), main(), main()

### Community 17 - "Harness"
Cohesion: 0.08
Nodes (15): LevelSmoother, Snapshot, State, calibrating, cooldown, idle, onset, speaking (+7 more)

### Community 19 - "ScheduledTaskService"
Cohesion: 0.09
Nodes (5): ScheduledTaskDao, ScheduledTask, TaskStatus, ScheduledTaskService, CurrentTimeTests

### Community 20 - "_most_recent_local_midnight_utc"
Cohesion: 0.07
Nodes (7): _most_recent_local_midnight_utc(), IsIdleTests, IsPastRolloverTests, build_service(), CheckForStaleConversationsTests, FakeConversationDao, MostRecentLocalMidnightUtcTests

### Community 21 - "test_meeting_service.py"
Cohesion: 0.07
Nodes (8): FakeAgentLoop, FakeClaudeService, FakeConversationDao, FakeEmbeddingService, FakeNotesDao, FakeUpdateService, RecoveryTests, ReplyQueue

### Community 22 - "json"
Cohesion: 0.08
Nodes (20): _remove(), transcribe_utterance(), _all(), await_ready(), check(), classify(), _entry(), kill_tree() (+12 more)

### Community 23 - "build_service"
Cohesion: 0.09
Nodes (10): build_service(), FakeClaudeResponse, FakeClaudeService, FakeConversationService, FakeEmbeddingService, FakeMemoryChunkDao, FakeTextBlock, FetchMemoryTests (+2 more)

### Community 24 - "MeetingError"
Cohesion: 0.12
Nodes (13): delete_meeting(), get_active_meeting(), get_meeting(), get_meeting_segments(), list_meetings(), _meeting_error(), regenerate_notes(), _resolve_meeting_id() (+5 more)

### Community 25 - "CursorService"
Cohesion: 0.17
Nodes (4): CursorService, CursorServiceError, CursorServiceTests, _FakeResponse

### Community 26 - "MeetingService"
Cohesion: 0.05
Nodes (4): MeetingDao, Meeting, MeetingStatus, MeetingService

### Community 27 - "FileOperationTests"
Cohesion: 0.09
Nodes (3): EditTests, FileOperationTests, PathContainmentTests

### Community 28 - "CodingSession"
Cohesion: 0.14
Nodes (4): CodingSessionDao, CodingEvent, CodingSession, CodingStatus

### Community 30 - "ConversationController"
Cohesion: 0.09
Nodes (8): Capture, ConversationController, .idleMessage, .isEnabled, .isWorking, .wakeWatching, Once, Sentry mode

### Community 31 - ".__init__"
Cohesion: 0.14
Nodes (6): _build_provider(), _ChainedProvider, OpenAITTS, _cartesia(), _eleven_labs(), _mock_chain()

### Community 32 - "Path"
Cohesion: 0.18
Nodes (8): current_commit(), DeployError, git_pull(), git_reset_hard(), run_git(), run_test_suite(), start_api(), start_worker()

### Community 33 - "test_auth_service.py"
Cohesion: 0.10
Nodes (4): NovaSessionDao, row_to_session(), NovaSession, RowConversionTests

### Community 35 - "auth_service.py"
Cohesion: 0.14
Nodes (9): _client_ip(), current_session(), list_sessions(), login(), logout(), AuthNotConfigured, BadCredentials, LockedOut (+1 more)

### Community 36 - "SessionManager"
Cohesion: 0.14
Nodes (3): _flatten(), Session, SessionManager

### Community 37 - "__main__.py"
Cohesion: 0.13
Nodes (7): Config, _flag(), load_env_file(), _configure_logging(), main(), _run(), _task()

### Community 38 - "Project"
Cohesion: 0.06
Nodes (8): ProjectDao, Project, CodeService, ProjectService, CodeServiceTestCase, FakeConversationDao, FakeProjectDao, ProjectResolutionTests

### Community 39 - "asyncio"
Cohesion: 0.05
Nodes (34): _all(), await_ready(), check(), classify(), _entry(), kill_tree(), _log_paths(), pid_alive() (+26 more)

### Community 40 - "DATGlassesCamera"
Cohesion: 0.10
Nodes (3): failed, notReady, DATGlassesCamera

### Community 44 - "Responsibility"
Cohesion: 0.16
Nodes (4): Responsibility, at(), DueTests, ReportMediumTests

### Community 45 - "McpOAuthService"
Cohesion: 0.22
Nodes (4): _b64url(), McpOAuthService, _origin(), _path()

### Community 46 - "make_update"
Cohesion: 0.16
Nodes (5): ConversationResolutionTests, make_update(), OpeningPromptTests, TwiMLTests, form()

### Community 47 - "recording_meeting"
Cohesion: 0.14
Nodes (6): CommitSegmentsTests, DeleteMeetingTests, FollowUpTests, explode(), recording_meeting(), UpdateMeetingTests

### Community 48 - "post"
Cohesion: 0.09
Nodes (18): logout_all(), adopt_claude_thread(), _authorized(), coding_socket(), coding_status(), get_coding_session(), list_claude_threads(), list_coding_sessions() (+10 more)

### Community 49 - "call_controller.py"
Cohesion: 0.10
Nodes (15): answer_call(), call_status(), _escape(), mint_relay_token(), _opening_prompt(), relay_socket(), start_turn(), run_after_previous() (+7 more)

### Community 51 - "ToolService"
Cohesion: 0.14
Nodes (6): ToolService, CountingService, FakeConversationService, FakeToolDao, GlassesCannotRecordMeetingsTests, get_all()

### Community 52 - "TurnTimer"
Cohesion: 0.10
Nodes (8): _emit(), TurnTimer, _drain(), _FakeMessage, _FakeStream, _FakeUsage, TurnStreamUsageMarkTests, TurnTimerTests

### Community 53 - "VisionService"
Cohesion: 0.07
Nodes (12): _allowed_origins(), lifespan(), capture_failed(), upload_image(), AuthGate, bearer_token(), _header(), is_exempt() (+4 more)

### Community 54 - "AuthService"
Cohesion: 0.12
Nodes (3): AuthService, _hash_token(), ConfigurationTests

### Community 55 - "run_migrations.py"
Cohesion: 0.17
Nodes (4): main(), migration_files(), _jsonable(), SQLService

### Community 56 - "build_service"
Cohesion: 0.08
Nodes (11): build_service(), CreateTests, FakeProjectDao, FakeTaskDao, FakeUpdateService, ListAndCancelTests, pending(), RecoverStuckTests (+3 more)

### Community 58 - "FakePersonaDao"
Cohesion: 0.14
Nodes (7): build_service(), CachingTests, FakePersonaDao, LoadingTests, seed_row(), ToolFacingWrapperTests, VersioningAndRollbackTests

### Community 59 - "ConversationLoopStreamTests"
Cohesion: 0.16
Nodes (4): ConversationLoopStreamTests, fake_stream(), fake_stream(), EventStreamTests

### Community 61 - "SpeechPlayer"
Cohesion: 0.07
Nodes (7): MP3StreamDecoder, PlaybackWatchdog, SpeechPlayer, .isBusy, .now, Stream, PlaybackWatchdogTests

### Community 63 - ".look"
Cohesion: 0.16
Nodes (10): Vision: "Hey Nova, what do you see?", Client → server, Connecting, Deviations from the brief and additions, Interjections, Prompt and tools, Server → client, Sidekick protocol: `WS /ws/sidekick` (+2 more)

### Community 64 - "FakeCamera"
Cohesion: 0.21
Nodes (4): FakeCamera, FakeVision, settle(), VisionControllerTests

### Community 65 - "ConversationControllerTests"
Cohesion: 0.06
Nodes (11): ConversationControllerTests, ConversationControllerTests.Rig, FakePlayer, .isBusy, FakeWake, Item, ManualScheduler, Rig (+3 more)

### Community 67 - "test_background_agent.py"
Cohesion: 0.16
Nodes (9): fake_get_response(), FakeConversationService, FakeMessage, FakeProjectDao, FakeTextBlock, FakeToolDao, FakeUpdateService, fake_get_response() (+1 more)

### Community 68 - "ClientEvent"
Cohesion: 0.04
Nodes (50): Phase, idle, listening, off, sentryBlocked, speaking, thinking, PhotoSlot (+42 more)

### Community 70 - "Conversation"
Cohesion: 0.04
Nodes (19): PromptSourceEnum, _is_stale(), resolve_sms_conversation(), _run_sms_turn(), MessageDao, Conversation, Message, MessageRole (+11 more)

### Community 71 - "nova_controller.py"
Cohesion: 0.06
Nodes (25): _canonical_wake_text(), chat_stream(), event_source(), get_nova_power(), get_nova_state(), has_stop_phrase(), has_wake_phrase(), normalize_wake_text() (+17 more)

### Community 72 - "McpServer"
Cohesion: 0.20
Nodes (3): McpServer, _now(), _parse_expiry()

### Community 74 - "TwilioService"
Cohesion: 0.07
Nodes (12): backend_url(), close_current_conversation(), fetch_conversation_info(), fetch_health(), fetch_projects(), fetch_tools(), stream_reply(), main() (+4 more)

### Community 76 - "AgentLoop"
Cohesion: 0.05
Nodes (7): AgentLoop, deliver(), mark_first_speech(), persist(), _memory_block_budget_seconds(), strip_expects_reply(), _strip_expects_reply_events()

### Community 77 - "faces_controller.py"
Cohesion: 0.12
Nodes (10): add_sample(), create_person(), delete_person(), _enroll(), list_people(), read_jpeg_body(), DuplicatePerson, EnrollmentError (+2 more)

### Community 78 - ".durationMs"
Cohesion: 0.16
Nodes (4): PCMFormat, PreRollBuffer, .count, AudioFramingTests

### Community 79 - "parse_gate_reply"
Cohesion: 0.18
Nodes (3): parse_gate_reply(), SidekickGate, GateReplyTests

### Community 80 - "CameraError"
Cohesion: 0.14
Nodes (10): APIError, badResponse, .errorDescription, server, unauthorized, CameraError, .errorDescription, glassesAudioNotUp (+2 more)

### Community 81 - "fake_stream"
Cohesion: 0.15
Nodes (6): fake_stream(), FailureHistoryAndRetryTests, fake_stream(), fake_stream(), fake_stream(), _FakeBadRequestError

### Community 83 - "FakeMcpServerDao"
Cohesion: 0.17
Nodes (3): build_service(), FakeMcpServerDao, McpServerServiceTests

### Community 88 - "test_sms.py"
Cohesion: 0.16
Nodes (4): BipConfigurationError, BipRequestError, is_permanent_bip_error(), user_phone_number()

### Community 89 - "test_responsibility_service.py"
Cohesion: 0.15
Nodes (5): build_service(), CheckForResponsibilitiesTests, FakeProjectDao, FakeUpdateService, WindowTests

### Community 92 - "build_memory_service"
Cohesion: 0.26
Nodes (5): build_memory_service(), FakeEmbeddingService, FakeMemoryChunkDao, match(), RetrieveContextTests

### Community 93 - "meeting_service.py"
Cohesion: 0.08
Nodes (5): BaseDao, MeetingChunkDao, MeetingNotesDao, MeetingChunk, MeetingNotes

### Community 94 - "ASRService"
Cohesion: 0.07
Nodes (14): main(), ASRService, drop_hallucination(), _hotwords(), _load_parakeet(), missing_cuda_libraries(), _nvidia_wheel_dll_dirs(), _platform_default_provider() (+6 more)

### Community 96 - "UpdateService"
Cohesion: 0.05
Nodes (9): UpdateDao, DeliveryStatus, ReportType, Update, EmailService, _env_int(), UpdateDeliveryService, UpdateService (+1 more)

### Community 97 - "Mac code agent daemon"
Cohesion: 0.16
Nodes (14): Nova code agent (Mac) README, Anthropic API key stripping, Mac dials out design, Per-session git worktree, Known limits (awake Mac, bounded replay, cache cost), launchd install and menu app, Mac code agent daemon, NOVA_CODE_TOKEN shared secret (+6 more)

### Community 98 - "test_spoken_reply.py"
Cohesion: 0.12
Nodes (8): _clamp(), clamp_spoken(), _comparable(), is_repeat(), strip_speak_tags(), ClampSpokenTests, IsRepeatTests, StripSpeakTagsTests

### Community 99 - "SpokenProse"
Cohesion: 0.17
Nodes (4): _plain_text(), SpokenProse, _said(), SpokenProseTests

### Community 100 - "MeetingSegment"
Cohesion: 0.13
Nodes (6): MeetingSegment, ChunkingTests, FinalizeTests, NotesTests, NotesUseNoToolsTests, TranscriptTests

### Community 101 - "._run_begin"
Cohesion: 0.23
Nodes (6): BeginFlowTests, fake_get(), fake_post(), fake_post(), fake_post(), FakeResponse

### Community 102 - "BipService"
Cohesion: 0.17
Nodes (3): BipService, _describe_response_error(), _parse_number_list()

### Community 104 - "Keys"
Cohesion: 0.08
Nodes (23): Keys, assistantText, bytes, chunkBase64, client, code, conversationId, count (+15 more)

### Community 106 - "model/__init__.py"
Cohesion: 0.12
Nodes (4): MemoryChunkDao, MemoryChunk, MemoryMatch, ServiceMethodToolConfig

### Community 108 - "build_service"
Cohesion: 0.14
Nodes (5): build_service(), FakeProjectDao, RetrievalTests, StartMeetingTests, StopMeetingTests

### Community 110 - "DeployService"
Cohesion: 0.13
Nodes (4): DeployService, HealthTimeoutTests, CheckDeployStatusTests, DeployMainTests

### Community 111 - "FakeDao"
Cohesion: 0.18
Nodes (4): CompleteAndRefreshTests, ConnectorFilteringTests, FakeDao, oauth_server()

### Community 112 - ".run_turn"
Cohesion: 0.08
Nodes (13): FakeMessage, FakeTextBlock, FakeToolDao, FakeUpdateService, MemoryInjectionTests, fake_stream(), boom(), notification() (+5 more)

### Community 113 - "make_guard"
Cohesion: 0.29
Nodes (5): _contained(), make_guard(), can_use_tool(), health(), root()

### Community 114 - "AppModel"
Cohesion: 0.06
Nodes (21): AppModel, .serverURLString, NovaGlassesApp, .body, RootView, .body, AuthStore, .baseQuery (+13 more)

### Community 115 - "asr-bench.py"
Cohesion: 0.36
Nodes (4): cut_clips(), default_audio(), load(), main()

### Community 116 - "FakeMessage"
Cohesion: 0.19
Nodes (4): FakeMessage, StatusTextTests, TurnStreamTests, get_final_message()

### Community 117 - ".create_person"
Cohesion: 0.29
Nodes (3): face_row(), FaceServiceTests, unit()

### Community 119 - "Foundation"
Cohesion: 0.10
Nodes (12): AudioToolbox, AVFoundation, Foundation, ImageIO, ImagePrep, MWDATCamera, MWDATCore, Observation (+4 more)

### Community 120 - "Earcon"
Cohesion: 0.12
Nodes (15): Earcons, Note, Earcon, cancel, done, error, shutter, sidekickCue (+7 more)

### Community 125 - "worker.py"
Cohesion: 0.16
Nodes (10): BuildJobsTests, build_jobs(), _recover_stuck_tasks(), _run_check_for_responsibilities(), _run_check_for_stale_conversations(), _run_deliver_pending_updates(), _run_process_conversations(), _run_scheduled_tasks() (+2 more)

### Community 126 - "SidekickController"
Cohesion: 0.09
Nodes (15): Cancellable, ConversationIdStore, EarconPlaying, GlassesCamera, MainScheduler, NovaSocketing, Scheduling, SpeechPlaying (+7 more)

### Community 127 - "test_deploy_main.py"
Cohesion: 0.15
Nodes (6): DryRunTests, FailingTestsAbortTests, HappyPathTests, RollbackPathTests, _runner(), _silent_logger()

### Community 128 - "FakeConversationService"
Cohesion: 0.22
Nodes (3): FakeConversationService, FakeMcpService, FakeToolDao

### Community 130 - "FakeDao"
Cohesion: 0.14
Nodes (3): GateTestCase, WebSocketGateTests, FakeDao

### Community 132 - "build_app"
Cohesion: 0.22
Nodes (3): build_app(), stream(), fake_stream()

### Community 134 - "AuthenticateTests"
Cohesion: 0.12
Nodes (3): AuthenticateTests, AuthServiceTestCase, LoginTests

### Community 135 - "history_compaction.py"
Cohesion: 0.20
Nodes (15): _block_chars(), cap_messages(), clear_old_tool_results(), _clearable_blocks(), compact_history(), _env_int(), _is_plain_user_turn(), _history() (+7 more)

### Community 137 - "SidekickConnection"
Cohesion: 0.16
Nodes (3): Utterances, sidekick_socket(), SidekickConnection

### Community 139 - ".add"
Cohesion: 0.14
Nodes (6): AudioLog, Entry, AudioRouteManager, Route, .summary, .body

### Community 141 - "NovaGlasses"
Cohesion: 0.29
Nodes (6): Build and test (CLI), Code map, How it behaves, Install on your iPhone, NovaGlasses, On-device field checklist

### Community 144 - "ImageStore"
Cohesion: 0.18
Nodes (4): ImageStore, VisionImage, ContentBlocksTests, ImageStoreTests

### Community 146 - "sessions.py"
Cohesion: 0.20
Nodes (3): _as_int(), _is_prose(), _ms_to_iso()

### Community 154 - ".conversation_loop_events"
Cohesion: 0.11
Nodes (14): fake_stream(), PrefetchedConversationTests, fake_stream(), fake_stream(), fake_stream(), fake_stream(), fake_stream(), fake_stream() (+6 more)

### Community 156 - "fetch_face_models.py"
Cohesion: 0.36
Nodes (3): fetch(), main(), sha256()

### Community 158 - "PassSentinelTests"
Cohesion: 0.10
Nodes (11): is_sidekick_pass(), _agent_loop(), FakeMessage, FakeTextBlock, FakeToolDao, FakeToolUseBlock, _live(), get_final_message() (+3 more)

### Community 159 - "deploy_main.py"
Cohesion: 0.21
Nodes (6): build_logger(), check_health_once(), DeployConfig, main(), _timestamp(), wait_for_health()

### Community 165 - "ClaudeCreditsService"
Cohesion: 0.14
Nodes (4): get_all_settings(), get_available_models(), get_claude_credits(), ClaudeCreditsService

### Community 170 - "worktree.py"
Cohesion: 0.22
Nodes (7): create(), _git(), remove(), resolve_repo(), slugify(), Workspace, WorktreeError

### Community 172 - "FakeHttp"
Cohesion: 0.20
Nodes (5): build_service(), FakeHttp, InfobipRequestTests, RecipientAllowlistTests, SendSmsTests

### Community 173 - "CommandLineService"
Cohesion: 0.07
Nodes (3): CommandLineService, BackgroundTests, ForegroundTests

### Community 176 - "dict"
Cohesion: 0.23
Nodes (3): basic(), InboundSecretTests, SenderAllowlistTests

### Community 177 - "VisionRoutesTests"
Cohesion: 0.26
Nodes (3): Identification, FakeFaceService, VisionRoutesTests

### Community 181 - "AddPersonView"
Cohesion: 0.24
Nodes (6): .api, AddPersonView, .body, FacesView, .body, PhotosUI

### Community 183 - ".setUp"
Cohesion: 0.12
Nodes (4): DirectTurnCounterTests, fake_transcribe(), FakeGate, FakeSidekickLoop

### Community 184 - "DeployRunner"
Cohesion: 0.26
Nodes (3): DeployRunner, find_pid_on_port(), find_worker_pid()

### Community 186 - "os"
Cohesion: 0.05
Nodes (18): host_environment_prompt(), _host_kind(), _machine_line(), stop_pid(), main(), one_call(), main(), one_call() (+10 more)

### Community 189 - "sidekick_service.py"
Cohesion: 0.21
Nodes (3): has_be_quiet_phrase(), _normalize(), BeQuietPhraseTests

### Community 191 - "MacSessionLifecycleTests"
Cohesion: 0.10
Nodes (3): MacConcurrentSessionTests, MacSessionLifecycleTests, sink()

### Community 192 - "XCTestCase"
Cohesion: 0.09
Nodes (8): AudioSessionPolicy, AudioSessionPolicyTests, AmbientForwardingTests, WakePhraseAloneTests, WakeStraightToListeningTests, What is verified and what is not, NovaGlasses, XCTest

### Community 194 - "ElevenLabsService"
Cohesion: 0.23
Nodes (3): _describe_failure(), ElevenLabsService, ElevenLabsRequestTests

### Community 195 - "conversation_controller.py"
Cohesion: 0.27
Nodes (5): close_conversation(), get_conversation(), get_conversation_messages(), _parse_uuid(), _project_payload()

### Community 196 - "InterruptedToolCallTests"
Cohesion: 0.26
Nodes (3): FakeToolUseBlock, InterruptedToolCallTests, _call()

### Community 205 - "match"
Cohesion: 0.38
Nodes (3): GalleryPerson, match(), MatchTests

### Community 207 - "_FakeTable"
Cohesion: 0.13
Nodes (4): CheckForStaleConversationsLoopTests, _FakeResponse, _FakeSupabaseClient, _FakeTable

### Community 212 - "protocol.py"
Cohesion: 0.39
Nodes (3): _artifact_for(), encode(), _truncate()

### Community 216 - "meeting_socket"
Cohesion: 0.39
Nodes (6): transcribe_segments_serialized(), meeting_socket(), capture_loop(), flush_tail(), send(), _transcribe_tail()

### Community 220 - "test_glasses_voice.py"
Cohesion: 0.06
Nodes (16): Server behaviour, audio_file_bytes(), is_raw_pcm(), _pcm_params(), suffix_for_mime(), transcribe_serialized(), _broadcast(), face_socket() (+8 more)

## Ambiguous Edges - Review These
- `TTS conversion enhancer prompt (empty)` → `Voice mode tone guidelines`  [AMBIGUOUS]
  prompting/tts_conversion_enhancer_prompt.txt · relation: conceptually_related_to

## Knowledge Gaps
- **165 isolated node(s):** `UserNotifications`, `.serverURLString`, `.summary`, `AudioToolbox`, `.count` (+160 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1645 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **106 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `TTS conversion enhancer prompt (empty)` and `Voice mode tone guidelines`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `NovaGlasses` connect `NovaGlasses` to `XCTestCase`, `ConversationController`, `.look`?**
  _High betweenness centrality (0.318) - this node is a cross-community bridge._
- **Are the 43 inferred relationships involving `AgentLoop` (e.g. with `Server behaviour` and `PromptEnums`) actually correct?**
  _`AgentLoop` has 43 INFERRED edges - model-reasoned connections that need verification._
- **What connects `UserNotifications`, `.serverURLString`, `.summary` to the rest of the system?**
  _165 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `SimpleFinancesService` be split into smaller, more focused modules?**
  _Cohesion score 0.1069182389937107 - nodes in this community are weakly interconnected._
- **Why does `Vision: "Hey Nova, what do you see?"` connect `.look` to `NovaGlasses`?**
  _High betweenness centrality (0.317) - this node is a cross-community bridge._
- **Are the 21 inferred relationships involving `Conversation` (e.g. with `_is_stale()` and `ConversationDao`) actually correct?**
  _`Conversation` has 21 INFERRED edges - model-reasoned connections that need verification._