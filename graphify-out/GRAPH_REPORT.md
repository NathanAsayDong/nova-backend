# Graph Report - silent-mode-backend  (2026-11-24)

## Corpus Check
- 243 files · ~228,770 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 12 file(s) not represented in the graph (top: (none) 4, .mdc 1, .pbxproj 1)

## Summary
- 5574 nodes · 13033 edges · 253 communities (139 shown, 114 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 1389 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e3ad26ee`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- os
- UpdateDeliveryService
- SimpleFinancesService
- text
- TranscribeSocketTests
- OpenAILoopTests
- faces_controller.py
- AgentLoopImageTests
- test_background_agent.py
- ._env
- make_update
- ClaudeService
- GithubService
- build_service
- Nova system prompt (persona)
- .add
- subprocess
- Harness
- CodingService
- ScheduledTask
- _most_recent_local_midnight_utc
- test_meeting_service.py
- process_supervisor.py
- build_service
- normalize_report_types
- CursorService
- MeetingService
- FileOperationTests
- AppModel
- CodeService
- ConversationController
- ServerEvent
- time
- NovaSession
- ._conversation_turn
- match
- SessionManager
- _runner
- _silent_logger
- processes.py
- DATGlassesCamera
- VisionService
- .conversation_loop_events
- ResponsibilityService
- Responsibility
- .begin
- make_update
- build_service
- asyncio
- call_controller.py
- McpServerService
- AgentLoop
- TurnTimer
- auth_gate.py
- AuthService
- test_code_service.py
- build_service
- FakeTextBlock
- FakePersonaDao
- ConversationLoopStreamTests
- test_sms.py
- SpeechPlayer
- EndpointDecisionTests
- .look
- FakeCamera
- ConversationControllerTests
- ._artifact_for_tool
- BaseDao
- ClientEvent
- SentryModeTests
- Conversation
- agent_loop.py
- McpServer
- PersonaService
- TwilioService
- HttpGateTests
- Any
- transcribe_socket
- Tool
- parse_gate_reply
- is_nova_interrupt_phrase
- CameraError
- mcp_server_controller.py
- FakeMcpServerDao
- FakeMeetingDao
- CrudTests
- SettingsService
- CodingSession
- bip_service.py
- test_responsibility_service.py
- StreamedSpeechTests
- test_deploy_main.py
- build_memory_service
- Project
- ASRService
- sessions.py
- UpdateService
- Mac code agent daemon
- SpokenProse
- SpeechWakeDetector
- AgentBindingTests
- ._run_begin
- BipService
- NovaSocket
- Rig
- asr_service.py
- sms_controller.py
- CompletionNotificationTests
- ElevenLabsService
- .repair_tool_pairing
- .deploy_main
- McpOAuthService
- .run_turn
- TwilioErrorClassificationTests
- Person
- asr-bench.py
- .test_a_live_turn_reads_deltas_then_exposes_the_message
- FakeAgentLoop
- APIClient
- Foundation
- Earcon
- SidekickSocketTests
- FakePlayer
- EndSessionTests
- SidekickSession
- worker.py
- DeployService
- email_service.py
- __main__.py
- .completed
- AuthenticateTests
- ClassificationTests
- test_memory_injection.py
- ._spoken_track
- pending
- history_compaction.py
- AsrLock
- SidekickConnection
- test_coding_service.py
- AudioRouteManager
- .isOnlyWakePhrase
- .durationMs
- .sanitize_mcp_history
- PerformTests
- run_migrations.py
- SilentModeStatePushTests
- MacSessionLifecycleTests
- test_process_supervisor.py
- FakeSendWebSocket
- FallbackChainTests
- SpokenTrackTests
- Double
- LiveScreenTests
- ImageStore
- test_asr_filters.py
- MemoryChunkService
- FailureSpeechTests
- host_environment_prompt.py
- PassSentinelTests
- .__init__
- CLAUDE.md
- split_wake_phrase
- install.sh
- uninstall.sh
- ClaudeCreditsService
- nova-backend
- worktree.py
- CurrentModelTests
- FakeHttp
- CommandLineService
- DemoService
- MeetingError
- dict
- RelayTokenTests
- VisionRoutesTests
- CaptureEngine
- AddPersonView
- PersonaPrompt
- .setUp
- ScheduledTaskService
- shell.py
- replay_request.py
- fake_stream
- SelfKillHazardTests
- SpawnStaleAncestorHelperTimingTests
- HostEnvironmentPromptTests
- .setUp
- ReportMediumTests
- .wantsToSee
- GoodbyeTimingTests
- TTSService
- InterruptedToolCallTests
- CooldownTests
- FakePersonDao
- prepare
- test_persona_service.py
- FakeUpdateService
- MacShellTests
- ._to_dict
- FakeMessage
- FaceService
- AgentLink
- _FakeTable
- FakeUpdateService
- FakeTaskDao
- FakeResponse
- FinishedSessionTowerTests
- ReplyTests
- FallbackTests
- PromptSourceTests
- FakeResponsibilityDao
- ToolServiceTests
- NovaGlasses
- FakeDao
- SidekickService
- Entry
- Handle
- ThinkingPulseTests
- .iter_sentence_chunks
- ResponsibilityDeliveryTests
- ProviderSelectionTests
- Link
- protocol.py
- .split_sms_body
- test_settings_service.py
- VisionClient
- GlassesSocketTests
- CreateScheduleRequirementTests
- TranscribeUtteranceTests
- ServiceMethodToolConfig
- ToolRegistrationTests
- get_nova_power
- ProjectResolutionTests
- SilentModeStateOnConnectTests
- ToolUseStarted
- test_auth_gate.py
- auth_service.py
- SenderGateTests
- FakeChunkDao
- FakeConversationService
- tool_controller.py
- _describe_failure

## God Nodes (most connected - your core abstractions)
1. `AgentLoop` - 135 edges
2. `Conversation` - 94 edges
3. `ConversationController` - 85 edges
4. `ToolService` - 72 edges
5. `build_service()` - 57 edges
6. `ConversationService` - 56 edges
7. `CodingService` - 55 edges
8. `Responsibility` - 54 edges
9. `MeetingService` - 52 edges
10. `UpdateService` - 50 edges

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

## Communities (253 total, 114 thin omitted)

### Community 0 - "os"
Cohesion: 0.09
Nodes (12): _allowed_origins(), _build_file_logger(), _default_log_path(), mark(), _timing_enabled(), _env_flag(), _maybe_dump_request(), _caption_floor() (+4 more)

### Community 1 - "UpdateDeliveryService"
Cohesion: 0.12
Nodes (3): user_phone_number(), _env_int(), UpdateDeliveryService

### Community 2 - "SimpleFinancesService"
Cohesion: 0.11
Nodes (6): SimplApiError, SimplConfigurationError, SimpleFinancesService, response(), SimpleFinancesServiceTest, SimplFinancesToolRegistrationTest

### Community 3 - "text"
Cohesion: 0.22
Nodes (4): AuthenticationTests, forward(), PathTokenRouteTests, text()

### Community 5 - "OpenAILoopTests"
Cohesion: 0.16
Nodes (7): FakeClient, FakeFunctionCall, FakeResponse, FakeResponsesAPI, FakeTool, FakeToolService, OpenAILoopTests

### Community 6 - "faces_controller.py"
Cohesion: 0.14
Nodes (9): add_sample(), create_person(), delete_person(), _enroll(), list_people(), DuplicatePerson, EnrollmentError, FaceModelsMissing (+1 more)

### Community 7 - "AgentLoopImageTests"
Cohesion: 0.33
Nodes (4): AgentLoopImageTests, FakeMessage, FakeTextBlock, FakeToolUseBlock

### Community 8 - "test_background_agent.py"
Cohesion: 0.05
Nodes (16): BackgroundAgentLimitTests, never_finishes(), BackgroundAgentTests, fake_get_response(), FakeConversationService, FakeMessage, FakeProjectDao, FakeTextBlock (+8 more)

### Community 10 - "make_update"
Cohesion: 0.12
Nodes (13): at(), BadgeOnlyTests, build_service(), CallDeliveryTests, EmailDeliveryTests, make_update(), MultiChannelDeliveryTests, QuietHoursTests (+5 more)

### Community 11 - "ClaudeService"
Cohesion: 0.07
Nodes (7): ModelSwitchRequest, set_model(), _env_flag(), ClaudeService, _maybe_print_prompt(), GenerationKwargsTests, ClaudeServiceMcpKwargsTests

### Community 12 - "GithubService"
Cohesion: 0.15
Nodes (4): GithubService, GithubServiceError, _FakeResponse, GithubServiceTests

### Community 13 - "build_service"
Cohesion: 0.05
Nodes (10): build_service(), CreateUpdateTests, FakeConversationDao, FakeProjectDao, FakeUpdateDao, make_update(), MultiChannelReportTypeTests, NotificationQueueFieldsTests (+2 more)

### Community 14 - "Nova system prompt (persona)"
Cohesion: 0.07
Nodes (28): Hosting Nova off the home network, Backend environment variables, Cloudflare Tunnel (nova-tower, cloudflared), Firebase Hosting frontend (nova-voice-nd.web.app), Infobip SMS integration (/sms/inbound), Failed-login lockout policy, Mac coding agent (/ws/coding), MCP OAuth callback (+20 more)

### Community 15 - ".add"
Cohesion: 0.08
Nodes (15): Cancellable, ConversationIdStore, EarconPlaying, GlassesCamera, MainScheduler, NovaSocketing, Scheduling, SpeechPlaying (+7 more)

### Community 16 - "subprocess"
Cohesion: 0.12
Nodes (8): DeployRunner, find_all_worker_pids(), find_worker_pid(), _parent_pid_map(), _protected_pids(), run_test_suite(), spawn_stale_ancestor_helper(), stop_pid()

### Community 17 - "Harness"
Cohesion: 0.08
Nodes (15): LevelSmoother, Snapshot, State, calibrating, cooldown, idle, onset, speaking (+7 more)

### Community 19 - "ScheduledTask"
Cohesion: 0.12
Nodes (3): ScheduledTaskDao, ScheduledTask, TaskStatus

### Community 20 - "_most_recent_local_midnight_utc"
Cohesion: 0.07
Nodes (7): _most_recent_local_midnight_utc(), IsIdleTests, IsPastRolloverTests, build_service(), CheckForStaleConversationsTests, FakeConversationDao, MostRecentLocalMidnightUtcTests

### Community 21 - "test_meeting_service.py"
Cohesion: 0.06
Nodes (11): MeetingSegment, FakeAgentLoop, FakeClaudeService, FakeConversationDao, FakeEmbeddingService, FakeNotesDao, FakeUpdateService, FinalizeTests (+3 more)

### Community 22 - "process_supervisor.py"
Cohesion: 0.10
Nodes (18): _all(), await_ready(), check(), classify(), _entry(), kill_tree(), _log_paths(), pid_alive() (+10 more)

### Community 23 - "build_service"
Cohesion: 0.08
Nodes (10): build_service(), FakeClaudeService, FakeConversationService, FakeEmbeddingService, FakeMemoryChunkDao, FetchMemoryTests, ProcessConversationsTests, boom() (+2 more)

### Community 24 - "normalize_report_types"
Cohesion: 0.16
Nodes (3): encode_report_types(), normalize_report_types(), NormalizeAndEncodeReportTypesTests

### Community 25 - "CursorService"
Cohesion: 0.17
Nodes (4): CursorService, CursorServiceError, CursorServiceTests, _FakeResponse

### Community 26 - "MeetingService"
Cohesion: 0.06
Nodes (3): MeetingDao, Meeting, MeetingService

### Community 27 - "FileOperationTests"
Cohesion: 0.13
Nodes (3): CodeServiceTestCase, EditTests, FileOperationTests

### Community 28 - "AppModel"
Cohesion: 0.05
Nodes (21): AppModel, .serverURLString, NovaGlassesApp, .body, RootView, .body, AuthStore, .baseQuery (+13 more)

### Community 30 - "ConversationController"
Cohesion: 0.09
Nodes (10): Capture, ConversationController, .currentConversationId, .idleMessage, .isEnabled, .isWorking, .wakeWatching, Once (+2 more)

### Community 31 - "ServerEvent"
Cohesion: 0.03
Nodes (52): Keys, assistantText, bytes, chunkBase64, client, code, conversationId, count (+44 more)

### Community 32 - "time"
Cohesion: 0.11
Nodes (18): build_logger(), check_health_once(), current_commit(), DeployConfig, DeployError, _ensure_single_healthy_api(), find_all_pids_on_port(), find_pid_on_port() (+10 more)

### Community 33 - "NovaSession"
Cohesion: 0.10
Nodes (4): NovaSessionDao, row_to_session(), NovaSession, RowConversionTests

### Community 34 - "._conversation_turn"
Cohesion: 0.08
Nodes (5): _memory_block_budget_seconds(), strip_expects_reply(), _strip_expects_reply_events(), LiveReply, LiveReplyTests

### Community 35 - "match"
Cohesion: 0.18
Nodes (6): GalleryPerson, match(), face_row(), FaceServiceTests, MatchTests, unit()

### Community 37 - "_runner"
Cohesion: 0.12
Nodes (5): DryRunTests, LeftoverSweepTests, RollbackPathTests, _runner(), SweepHandsOffStaleAncestorsTests

### Community 38 - "_silent_logger"
Cohesion: 0.12
Nodes (4): EnsureSingleHealthyApiTests, HelperModeCliTests, RunStaleAncestorHelperTests, _silent_logger()

### Community 39 - "processes.py"
Cohesion: 0.16
Nodes (16): _all(), await_ready(), check(), _entry(), kill_tree(), _log_paths(), pid_alive(), port_open() (+8 more)

### Community 40 - "DATGlassesCamera"
Cohesion: 0.10
Nodes (3): failed, notReady, DATGlassesCamera

### Community 41 - "VisionService"
Cohesion: 0.12
Nodes (3): is_image_block(), VisionService, LookToolTests

### Community 42 - ".conversation_loop_events"
Cohesion: 0.10
Nodes (9): persist(), CountingService, PrefetchedConversationTests, AgentLoopMcpTests, fake_stream(), fake_stream(), fake_stream(), FakeBlock (+1 more)

### Community 44 - "Responsibility"
Cohesion: 0.16
Nodes (4): Responsibility, at(), CheckForResponsibilitiesTests, DueTests

### Community 45 - ".begin"
Cohesion: 0.19
Nodes (3): _b64url(), _origin(), _path()

### Community 46 - "make_update"
Cohesion: 0.16
Nodes (5): ConversationResolutionTests, make_update(), OpeningPromptTests, TwiMLTests, form()

### Community 47 - "build_service"
Cohesion: 0.08
Nodes (14): build_service(), ChunkingTests, CommitSegmentsTests, DeleteMeetingTests, FakeProjectDao, FollowUpTests, explode(), NotesTests (+6 more)

### Community 48 - "asyncio"
Cohesion: 0.04
Nodes (42): lifespan(), _client_ip(), current_session(), list_sessions(), login(), logout(), logout_all(), adopt_claude_thread() (+34 more)

### Community 49 - "call_controller.py"
Cohesion: 0.08
Nodes (16): answer_call(), call_status(), _escape(), mint_relay_token(), _opening_prompt(), relay_socket(), start_turn(), run_after_previous() (+8 more)

### Community 51 - "AgentLoop"
Cohesion: 0.06
Nodes (15): AgentLoop, ToolService, ConversationLoopLimitTests, FailureHistoryAndRetryTests, FakeConversationService, FakeToolDao, GlassesCannotRecordMeetingsTests, get_all() (+7 more)

### Community 52 - "TurnTimer"
Cohesion: 0.10
Nodes (8): _emit(), TurnTimer, _drain(), _FakeMessage, _FakeStream, _FakeUsage, TurnStreamUsageMarkTests, TurnTimerTests

### Community 53 - "auth_gate.py"
Cohesion: 0.16
Nodes (6): AuthGate, bearer_token(), _header(), is_exempt(), ExemptionTests, SidekickAuthTests

### Community 54 - "AuthService"
Cohesion: 0.12
Nodes (3): AuthService, _hash_token(), ConfigurationTests

### Community 55 - "test_code_service.py"
Cohesion: 0.12
Nodes (3): FakeConversationDao, FakeProjectDao, PathContainmentTests

### Community 56 - "build_service"
Cohesion: 0.14
Nodes (6): build_service(), CreateTests, FakeProjectDao, FakeUpdateService, ListAndCancelTests, soon()

### Community 58 - "FakePersonaDao"
Cohesion: 0.13
Nodes (7): build_service(), CachingTests, FakePersonaDao, LoadingTests, seed_row(), ToolFacingWrapperTests, VersioningAndRollbackTests

### Community 59 - "ConversationLoopStreamTests"
Cohesion: 0.16
Nodes (4): ConversationLoopStreamTests, fake_stream(), fake_stream(), EventStreamTests

### Community 60 - "test_sms.py"
Cohesion: 0.26
Nodes (4): _handle_inbound(), normalize_phone_number(), SmsRecipientError, NormalizationTests

### Community 61 - "SpeechPlayer"
Cohesion: 0.07
Nodes (7): MP3StreamDecoder, PlaybackWatchdog, SpeechPlayer, .isBusy, .now, Stream, PlaybackWatchdogTests

### Community 62 - "EndpointDecisionTests"
Cohesion: 0.08
Nodes (7): caption_endpoint_decision(), endpoint_decision(), EndpointDecision, _score_transcript(), silence_budget_ms(), CaptionEndpointDecisionTests, EndpointDecisionTests

### Community 63 - ".look"
Cohesion: 0.16
Nodes (11): Vision: "Hey Nova, what do you see?", Client → server, Connecting, Deviations from the brief and additions, Interjections, Prompt and tools, Server behaviour, Server → client (+3 more)

### Community 64 - "FakeCamera"
Cohesion: 0.21
Nodes (4): FakeCamera, FakeVision, settle(), VisionControllerTests

### Community 67 - "BaseDao"
Cohesion: 0.08
Nodes (6): BaseDao, MeetingChunkDao, MeetingNotesDao, ResponsibilityDao, MeetingChunk, MeetingNotes

### Community 68 - "ClientEvent"
Cohesion: 0.04
Nodes (46): FrameConverter, Note, Phase, idle, listening, off, sentryBlocked, speaking (+38 more)

### Community 69 - "SentryModeTests"
Cohesion: 0.06
Nodes (8): AudioSessionPolicyTests, SentryModeTests, AmbientForwardingTests, WakePhraseAloneTests, WakeStraightToListeningTests, What is verified and what is not, NovaGlasses, XCTest

### Community 70 - "Conversation"
Cohesion: 0.05
Nodes (7): ConversationDao, Conversation, ConversationService, FakeConversationService, FakeConversationService, ConversationControllerSilentModeTests, ThreadResolutionTests

### Community 71 - "agent_loop.py"
Cohesion: 0.05
Nodes (12): PromptEnums, PromptSourceEnum, voice_prompt_source(), capture_failed(), TurnStream, has_be_quiet_phrase(), _normalize(), ToolExecutionError (+4 more)

### Community 72 - "McpServer"
Cohesion: 0.14
Nodes (4): McpServerDao, McpServer, _now(), _parse_expiry()

### Community 74 - "TwilioService"
Cohesion: 0.07
Nodes (12): backend_url(), close_current_conversation(), fetch_conversation_info(), fetch_health(), fetch_projects(), fetch_tools(), stream_reply(), main() (+4 more)

### Community 77 - "transcribe_socket"
Cohesion: 0.07
Nodes (24): audio_file_bytes(), is_raw_pcm(), _pcm_params(), suffix_for_mime(), transcribe_serialized(), idle_stopped_event(), parse_conversation_id(), parse_image_ids() (+16 more)

### Community 78 - "Tool"
Cohesion: 0.12
Nodes (7): main(), main(), main(), main(), ToolDao, Tool, FakeToolDao

### Community 79 - "parse_gate_reply"
Cohesion: 0.22
Nodes (3): parse_gate_reply(), SidekickGate, GateReplyTests

### Community 80 - "is_nova_interrupt_phrase"
Cohesion: 0.15
Nodes (4): is_nova_interrupt_phrase(), _normalize_tokens(), NegativeMatchTests, PositiveMatchTests

### Community 81 - "CameraError"
Cohesion: 0.14
Nodes (10): APIError, badResponse, .errorDescription, server, unauthorized, CameraError, .errorDescription, glassesAudioNotUp (+2 more)

### Community 82 - "mcp_server_controller.py"
Cohesion: 0.19
Nodes (5): _callback_page(), delete_mcp_server(), list_mcp_servers(), mcp_oauth_callback(), update_mcp_server()

### Community 83 - "FakeMcpServerDao"
Cohesion: 0.17
Nodes (3): build_service(), FakeMcpServerDao, McpServerServiceTests

### Community 87 - "CodingSession"
Cohesion: 0.14
Nodes (4): CodingSessionDao, CodingEvent, CodingSession, CodingStatus

### Community 88 - "bip_service.py"
Cohesion: 0.20
Nodes (3): BipConfigurationError, BipRequestError, is_permanent_bip_error()

### Community 89 - "test_responsibility_service.py"
Cohesion: 0.17
Nodes (4): build_service(), FakeProjectDao, FakeUpdateService, WindowTests

### Community 91 - "test_deploy_main.py"
Cohesion: 0.12
Nodes (4): FailingTestsAbortTests, HappyPathTests, SpawnStaleAncestorHelperTests, WaitForPidExitTests

### Community 92 - "build_memory_service"
Cohesion: 0.26
Nodes (5): build_memory_service(), FakeEmbeddingService, FakeMemoryChunkDao, match(), RetrieveContextTests

### Community 93 - "Project"
Cohesion: 0.20
Nodes (3): ProjectDao, Project, ProjectService

### Community 95 - "sessions.py"
Cohesion: 0.11
Nodes (9): _contained(), make_guard(), can_use_tool(), _as_int(), _flatten(), _is_prose(), _ms_to_iso(), health() (+1 more)

### Community 96 - "UpdateService"
Cohesion: 0.07
Nodes (5): UpdateDao, DeliveryStatus, ReportType, Update, UpdateService

### Community 97 - "Mac code agent daemon"
Cohesion: 0.16
Nodes (14): Nova code agent (Mac) README, Anthropic API key stripping, Mac dials out design, Per-session git worktree, Known limits (awake Mac, bounded replay, cache cost), launchd install and menu app, Mac code agent daemon, NOVA_CODE_TOKEN shared secret (+6 more)

### Community 98 - "SpokenProse"
Cohesion: 0.06
Nodes (16): deliver(), mark_first_speech(), _clamp(), clamp_spoken(), _comparable(), is_repeat(), _plain_text(), speech_summary() (+8 more)

### Community 101 - "._run_begin"
Cohesion: 0.26
Nodes (5): BeginFlowTests, fake_get(), fake_post(), fake_post(), FakeResponse

### Community 102 - "BipService"
Cohesion: 0.17
Nodes (3): BipService, _describe_response_error(), _parse_number_list()

### Community 103 - "NovaSocket"
Cohesion: 0.11
Nodes (7): .baseURL, SocketConnectionState, connected, connecting, disconnected, unauthorized, NovaSocket

### Community 104 - "Rig"
Cohesion: 0.18
Nodes (3): Rig, SidekickControllerTests, SidekickEventCodingTests

### Community 105 - "asr_service.py"
Cohesion: 0.20
Nodes (8): main(), _hotwords(), _load_parakeet(), missing_cuda_libraries(), _nvidia_wheel_dll_dirs(), _platform_default_provider(), _resolve_whisper_device(), _setup_cuda_libraries()

### Community 106 - "sms_controller.py"
Cohesion: 0.09
Nodes (12): chat_stream(), event_source(), sse_event(), _authorize(), inbound_sms(), inbound_sms_with_path_token(), _is_stale(), _receive() (+4 more)

### Community 108 - "ElevenLabsService"
Cohesion: 0.23
Nodes (3): _describe_failure(), ElevenLabsService, ElevenLabsRequestTests

### Community 110 - ".deploy_main"
Cohesion: 0.15
Nodes (3): HealthTimeoutTests, StopPidTreeKillTests, DeployMainTests

### Community 111 - "McpOAuthService"
Cohesion: 0.19
Nodes (6): McpOAuthService, fake_post(), CompleteAndRefreshTests, ConnectorFilteringTests, FakeDao, oauth_server()

### Community 112 - ".run_turn"
Cohesion: 0.10
Nodes (8): MemoryInjectionTests, boom(), notification(), NotificationCapTests, NotificationCrossMediumTests, NotificationRecencyTests, NotificationScopingTests, PendingNotificationsInjectionTests

### Community 113 - "TwilioErrorClassificationTests"
Cohesion: 0.14
Nodes (6): describe_twilio_error(), is_permanent_twilio_error(), SimpleNamespace_Exception, TwilioErrorClassificationTests, reject(), flake()

### Community 115 - "asr-bench.py"
Cohesion: 0.36
Nodes (4): cut_clips(), default_audio(), load(), main()

### Community 117 - "FakeAgentLoop"
Cohesion: 0.13
Nodes (3): FakeAgentLoop, SpeakQueuedLinesGatingTests, TTSProviderNeverCalledWhenSilentTests

### Community 119 - "Foundation"
Cohesion: 0.09
Nodes (13): AudioToolbox, AVFoundation, Foundation, ImageIO, AudioSessionPolicy, ImagePrep, MWDATCamera, MWDATCore (+5 more)

### Community 120 - "Earcon"
Cohesion: 0.13
Nodes (14): Earcons, Earcon, cancel, done, error, shutter, sidekickCue, sidekickOff (+6 more)

### Community 122 - "FakePlayer"
Cohesion: 0.19
Nodes (3): FakePlayer, .isBusy, FakeWake

### Community 125 - "worker.py"
Cohesion: 0.16
Nodes (10): BuildJobsTests, build_jobs(), _recover_stuck_tasks(), _run_check_for_responsibilities(), _run_check_for_stale_conversations(), _run_deliver_pending_updates(), _run_process_conversations(), _run_scheduled_tasks() (+2 more)

### Community 128 - "__main__.py"
Cohesion: 0.13
Nodes (7): Config, _flag(), load_env_file(), _configure_logging(), main(), _run(), _task()

### Community 129 - ".completed"
Cohesion: 0.11
Nodes (10): fake_stream(), fake_stream(), fake_stream(), fake_stream(), fake_stream(), fake_stream(), TurnStreamTests, get_final_message() (+2 more)

### Community 130 - "AuthenticateTests"
Cohesion: 0.12
Nodes (4): GateTestCase, AuthenticateTests, AuthServiceTestCase, LoginTests

### Community 132 - "test_memory_injection.py"
Cohesion: 0.08
Nodes (11): MemoryChunkDao, MessageDao, MemoryChunk, MemoryMatch, Message, MessageRole, FakeClaudeResponse, FakeTextBlock (+3 more)

### Community 134 - "pending"
Cohesion: 0.21
Nodes (4): pending(), RecoverStuckTests, RunDueTests, RunTests

### Community 135 - "history_compaction.py"
Cohesion: 0.20
Nodes (15): _block_chars(), cap_messages(), clear_old_tool_results(), _clearable_blocks(), compact_history(), _env_int(), _is_plain_user_turn(), _history() (+7 more)

### Community 137 - "SidekickConnection"
Cohesion: 0.12
Nodes (3): Utterances, sidekick_socket(), SidekickConnection

### Community 139 - "AudioRouteManager"
Cohesion: 0.22
Nodes (3): AudioRouteManager, Route, .summary

### Community 141 - ".durationMs"
Cohesion: 0.19
Nodes (4): PCMFormat, PreRollBuffer, .count, AudioFramingTests

### Community 144 - "run_migrations.py"
Cohesion: 0.17
Nodes (4): main(), migration_files(), _jsonable(), SQLService

### Community 145 - "SilentModeStatePushTests"
Cohesion: 0.11
Nodes (3): build_service(), SilentModeServiceTests, SilentModeStatePushTests

### Community 147 - "test_process_supervisor.py"
Cohesion: 0.13
Nodes (4): fetch(), main(), sha256(), MirrorTests

### Community 148 - "FakeSendWebSocket"
Cohesion: 0.09
Nodes (9): no_tts(), FakeSendWebSocket, InterruptAndCancelWiringTests, scenario(), scenario(), scenario(), SpeakOnCompletionTests, never_finishes() (+1 more)

### Community 151 - "Double"
Cohesion: 0.31
Nodes (3): ConversationControllerTests.Rig, Item, ManualScheduler

### Community 153 - "ImageStore"
Cohesion: 0.14
Nodes (5): ImageStore, _in_view_text(), VisionImage, ContentBlocksTests, ImageStoreTests

### Community 154 - "test_asr_filters.py"
Cohesion: 0.26
Nodes (4): drop_hallucination(), DropHallucinationTests, _segment(), WhisperSegmentFilterTests

### Community 155 - "MemoryChunkService"
Cohesion: 0.07
Nodes (5): EmbeddingService, MemoryChunkService, ParseChunksTests, SplitTranscriptTests, RetrievableQueryTests

### Community 157 - "host_environment_prompt.py"
Cohesion: 0.31
Nodes (3): host_environment_prompt(), _host_kind(), _machine_line()

### Community 158 - "PassSentinelTests"
Cohesion: 0.10
Nodes (9): is_sidekick_pass(), FakeMessage, FakeTextBlock, FakeToolUseBlock, FakeUpdateService, _live(), LookToolExclusionTests, fake_stream() (+1 more)

### Community 159 - ".__init__"
Cohesion: 0.14
Nodes (6): _build_provider(), _ChainedProvider, OpenAITTS, _cartesia(), _eleven_labs(), _mock_chain()

### Community 161 - "split_wake_phrase"
Cohesion: 0.17
Nodes (7): _canonical_wake_text(), has_stop_phrase(), has_wake_phrase(), normalize_wake_text(), split_wake_phrase(), SplitWakePhraseTests, WakePhraseTests

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

### Community 175 - "MeetingError"
Cohesion: 0.09
Nodes (19): transcribe_segments_serialized(), delete_meeting(), get_active_meeting(), get_meeting(), get_meeting_segments(), list_meetings(), _meeting_error(), meeting_socket() (+11 more)

### Community 176 - "dict"
Cohesion: 0.23
Nodes (3): basic(), InboundSecretTests, SenderAllowlistTests

### Community 178 - "VisionRoutesTests"
Cohesion: 0.26
Nodes (3): Identification, FakeFaceService, VisionRoutesTests

### Community 181 - "AddPersonView"
Cohesion: 0.24
Nodes (6): .api, AddPersonView, .body, FacesView, .body, PhotosUI

### Community 183 - ".setUp"
Cohesion: 0.12
Nodes (4): DirectTurnCounterTests, fake_transcribe(), FakeGate, FakeSidekickLoop

### Community 185 - "shell.py"
Cohesion: 0.27
Nodes (5): classify(), _clip(), _resolve_cwd(), run(), _scratch_pair()

### Community 186 - "replay_request.py"
Cohesion: 0.20
Nodes (5): main(), one_call(), main(), one_call(), variants()

### Community 187 - "fake_stream"
Cohesion: 0.14
Nodes (5): fake_stream(), fake_stream(), fake_stream(), fake_stream(), _FakeBadRequestError

### Community 196 - "InterruptedToolCallTests"
Cohesion: 0.26
Nodes (3): FakeToolUseBlock, InterruptedToolCallTests, _call()

### Community 199 - "prepare"
Cohesion: 0.27
Nodes (4): prepare(), jpeg(), phone(), PrepareTests

### Community 207 - "_FakeTable"
Cohesion: 0.13
Nodes (4): CheckForStaleConversationsLoopTests, _FakeResponse, _FakeSupabaseClient, _FakeTable

### Community 218 - "NovaGlasses"
Cohesion: 0.29
Nodes (6): Build and test (CLI), Code map, How it behaves, Install on your iPhone, NovaGlasses, On-device field checklist

### Community 222 - "Entry"
Cohesion: 0.36
Nodes (3): AudioLog, Entry, .body

### Community 230 - "protocol.py"
Cohesion: 0.39
Nodes (3): _artifact_for(), encode(), _truncate()

### Community 244 - "test_auth_gate.py"
Cohesion: 0.13
Nodes (4): build_app(), stream(), WebSocketGateTests, fake_stream()

### Community 247 - "SenderGateTests"
Cohesion: 0.23
Nodes (3): make_request(), SenderGateTests, go()

## Ambiguous Edges - Review These
- `TTS conversion enhancer prompt (empty)` → `Voice mode tone guidelines`  [AMBIGUOUS]
  prompting/tts_conversion_enhancer_prompt.txt · relation: conceptually_related_to

## Knowledge Gaps
- **167 isolated node(s):** `UserNotifications`, `.serverURLString`, `.summary`, `AudioToolbox`, `.count` (+162 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1783 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **114 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `TTS conversion enhancer prompt (empty)` and `Voice mode tone guidelines`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `NovaGlasses` connect `NovaGlasses` to `SentryModeTests`, `ConversationController`, `.look`?**
  _High betweenness centrality (0.310) - this node is a cross-community bridge._
- **Are the 45 inferred relationships involving `AgentLoop` (e.g. with `Server behaviour` and `PromptEnums`) actually correct?**
  _`AgentLoop` has 45 INFERRED edges - model-reasoned connections that need verification._
- **What connects `UserNotifications`, `.serverURLString`, `.summary` to the rest of the system?**
  _167 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `os` be split into smaller, more focused modules?**
  _Cohesion score 0.09103840682788052 - nodes in this community are weakly interconnected._
- **Why does `Vision: "Hey Nova, what do you see?"` connect `.look` to `NovaGlasses`?**
  _High betweenness centrality (0.310) - this node is a cross-community bridge._
- **Are the 23 inferred relationships involving `Conversation` (e.g. with `_is_stale()` and `ConversationDao`) actually correct?**
  _`Conversation` has 23 INFERRED edges - model-reasoned connections that need verification._