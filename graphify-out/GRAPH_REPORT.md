# Graph Report - nova-backend  (2026-11-13)

## Corpus Check
- 238 files · ~207,156 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: (none) 3, .mdc 1, .pbxproj 1)

## Summary
- 5132 nodes · 12058 edges · 207 communities (134 shown, 73 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 1287 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `39c9844f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Tool
- sms_controller.py
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
- test_vision.py
- ToolService
- Harness
- CodingService
- ScheduledTask
- _most_recent_local_midnight_utc
- processes.py
- json
- build_service
- MeetingError
- CursorService
- MeetingService
- FileOperationTests
- CodingSession
- UpdateDeliveryService
- ConversationController
- os
- time
- NovaSession
- LiveReply
- auth_service.py
- SessionManager
- __main__.py
- Project
- asyncio
- DATGlassesCamera
- Sendable
- pending
- ResponsibilityService
- Responsibility
- McpOAuthService
- make_update
- build_service
- post
- call_controller.py
- McpServerService
- requests
- TurnTimer
- auth_gate.py
- AuthService
- run_migrations.py
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
- test_background_agent.py
- ServerEvent
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
- re
- CameraError
- fake_stream
- LiveScreenTests
- FakeMcpServerDao
- FakeMeetingDao
- CrudTests
- SettingsService
- Person
- test_sms.py
- test_responsibility_service.py
- StreamedSpeechTests
- AgentBindingTests
- build_memory_service
- meeting_service.py
- ASRService
- AsrLock
- UpdateService
- Mac code agent daemon
- FakeTaskDao
- ServiceMethodToolConfig
- _FakeStream
- ._run_begin
- BipService
- NovaSocket
- Keys
- FaceService
- typing
- CompletionNotificationTests
- VoiceMode
- .repair_tool_pairing
- service/__init__.py
- FakeDao
- MemoryInjectionTests
- sessions.py
- AppModel
- asr-bench.py
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
- agent_loop.py
- ._to_dict
- FakeDao
- ClassificationTests
- build_app
- CaptureEngine
- ReportMediumTests
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
- .transcript
- ToolExecutionError
- .allowed_sms_senders
- TwilioErrorClassificationTests
- SpokenTrackTests
- .iter_sentence_chunks
- VisionService
- TurnStream
- MemoryChunkService
- test_process_supervisor.py
- FakeResponse
- test_sidekick.py
- Rig
- CLAUDE.md
- auth_controller.py
- install.sh
- uninstall.sh
- settings_controller.py
- nova-backend
- subprocess
- CurrentModelTests
- FakeHttp
- CommandLineService
- DemoService
- dict
- VisionRoutesTests
- AddPersonView
- PersonaPrompt
- .setUp
- GlassesSocketTests
- replay_request.py
- .wantsToSee
- unittest
- MacSessionLifecycleTests
- SentryModeTests
- split_wake_phrase
- conversation_controller.py
- InterruptedToolCallTests
- ThinkingPulseTests
- GuardrailTests
- FakeUpdateService
- Link
- AgentLink
- _FakeTable
- shell.py
- VisionClient
- FinishedSessionTowerTests
- protocol.py
- FallbackTests
- .split_sms_body
- main.py
- ScheduledTaskService
- test_persona_service.py
- get_nova_state

## God Nodes (most connected - your core abstractions)
1. `AgentLoop` - 121 edges
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

## Communities (207 total, 73 thin omitted)

### Community 0 - "Tool"
Cohesion: 0.12
Nodes (5): list_tools(), ToolDao, Tool, FakeToolDao, ToolServiceTests

### Community 1 - "sms_controller.py"
Cohesion: 0.16
Nodes (8): _authorize(), _handle_inbound(), inbound_sms(), inbound_sms_with_path_token(), _is_stale(), _receive(), resolve_sms_conversation(), _run_sms_turn()

### Community 2 - "SimpleFinancesService"
Cohesion: 0.11
Nodes (6): SimplApiError, SimplConfigurationError, SimpleFinancesService, response(), SimpleFinancesServiceTest, SimplFinancesToolRegistrationTest

### Community 3 - "text"
Cohesion: 0.16
Nodes (5): AuthenticationTests, forward(), PathTokenRouteTests, SenderGateTests, text()

### Community 5 - "test_openai_loop.py"
Cohesion: 0.18
Nodes (7): FakeClient, FakeFunctionCall, FakeResponse, FakeResponsesAPI, FakeTool, FakeToolService, OpenAILoopTests

### Community 6 - "Rig"
Cohesion: 0.13
Nodes (6): FakePlayer, .isBusy, FakeWake, Item, ManualScheduler, Rig

### Community 7 - "AgentLoopImageTests"
Cohesion: 0.26
Nodes (5): AgentLoopImageTests, fake_stream(), FakeMessage, FakeTextBlock, FakeToolUseBlock

### Community 8 - ".run_agent"
Cohesion: 0.10
Nodes (3): BackgroundAgentTests, ReportTypeTests, ResponsibilityRunToolRestrictionTests

### Community 9 - "._env"
Cohesion: 0.05
Nodes (10): CartesiaService, NovaService, TTSService, CartesiaRequestTests, CooldownTests, FallbackChainTests, refused(), _full_chain_env() (+2 more)

### Community 10 - "make_update"
Cohesion: 0.14
Nodes (11): at(), BadgeOnlyTests, build_service(), CallDeliveryTests, EmailDeliveryTests, make_update(), QuietHoursTests, SettleCallTests (+3 more)

### Community 11 - "ClaudeService"
Cohesion: 0.07
Nodes (6): _env_flag(), ClaudeService, _maybe_dump_request(), _maybe_print_prompt(), GenerationKwargsTests, ClaudeServiceMcpKwargsTests

### Community 12 - "GithubService"
Cohesion: 0.14
Nodes (4): GithubService, GithubServiceError, _FakeResponse, GithubServiceTests

### Community 13 - "build_service"
Cohesion: 0.07
Nodes (9): build_service(), CreateUpdateTests, FakeConversationDao, FakeProjectDao, FakeUpdateDao, make_update(), NotificationQueueFieldsTests, ReportTypeTests (+1 more)

### Community 14 - "Nova system prompt (persona)"
Cohesion: 0.07
Nodes (28): Hosting Nova off the home network, Backend environment variables, Cloudflare Tunnel (nova-tower, cloudflared), Firebase Hosting frontend (nova-voice-nd.web.app), Infobip SMS integration (/sms/inbound), Failed-login lockout policy, Mac coding agent (/ws/coding), MCP OAuth callback (+20 more)

### Community 15 - "test_vision.py"
Cohesion: 0.09
Nodes (10): capture_failed(), read_jpeg_body(), upload_image(), CaptureFailed, InvalidImage, prepare(), FakeConversationService, jpeg() (+2 more)

### Community 16 - "ToolService"
Cohesion: 0.22
Nodes (5): main(), main(), main(), main(), ToolService

### Community 17 - "Harness"
Cohesion: 0.08
Nodes (15): LevelSmoother, Snapshot, State, calibrating, cooldown, idle, onset, speaking (+7 more)

### Community 19 - "ScheduledTask"
Cohesion: 0.14
Nodes (3): ScheduledTaskDao, ScheduledTask, TaskStatus

### Community 20 - "_most_recent_local_midnight_utc"
Cohesion: 0.07
Nodes (7): _most_recent_local_midnight_utc(), IsIdleTests, IsPastRolloverTests, build_service(), CheckForStaleConversationsTests, FakeConversationDao, MostRecentLocalMidnightUtcTests

### Community 21 - "processes.py"
Cohesion: 0.16
Nodes (16): _all(), await_ready(), check(), _entry(), kill_tree(), _log_paths(), pid_alive(), port_open() (+8 more)

### Community 22 - "json"
Cohesion: 0.11
Nodes (18): _all(), await_ready(), check(), classify(), _entry(), kill_tree(), _log_paths(), pid_alive() (+10 more)

### Community 23 - "build_service"
Cohesion: 0.08
Nodes (10): build_service(), FakeClaudeService, FakeConversationService, FakeEmbeddingService, FakeMemoryChunkDao, FetchMemoryTests, ProcessConversationsTests, boom() (+2 more)

### Community 24 - "MeetingError"
Cohesion: 0.09
Nodes (19): transcribe_segments_serialized(), delete_meeting(), get_active_meeting(), get_meeting(), get_meeting_segments(), list_meetings(), _meeting_error(), meeting_socket() (+11 more)

### Community 25 - "CursorService"
Cohesion: 0.17
Nodes (4): CursorService, CursorServiceError, CursorServiceTests, _FakeResponse

### Community 26 - "MeetingService"
Cohesion: 0.05
Nodes (3): MeetingDao, Meeting, MeetingService

### Community 27 - "FileOperationTests"
Cohesion: 0.09
Nodes (3): EditTests, FileOperationTests, PathContainmentTests

### Community 28 - "CodingSession"
Cohesion: 0.14
Nodes (4): CodingSessionDao, CodingEvent, CodingSession, CodingStatus

### Community 29 - "UpdateDeliveryService"
Cohesion: 0.10
Nodes (3): EmailService, _env_int(), UpdateDeliveryService

### Community 30 - "ConversationController"
Cohesion: 0.10
Nodes (9): Capture, ConversationController, .idleMessage, .isEnabled, .isWorking, .wakeWatching, Once, WakeDetecting (+1 more)

### Community 31 - "os"
Cohesion: 0.08
Nodes (11): _describe_failure(), _describe_failure(), ElevenLabsService, _build_provider(), _ChainedProvider, OpenAITTS, _provider_cooldown_seconds(), _requested_provider() (+3 more)

### Community 32 - "time"
Cohesion: 0.09
Nodes (18): build_logger(), check_health_once(), current_commit(), DeployConfig, DeployError, DeployRunner, find_pid_on_port(), find_worker_pid() (+10 more)

### Community 33 - "NovaSession"
Cohesion: 0.10
Nodes (4): NovaSessionDao, row_to_session(), NovaSession, RowConversionTests

### Community 34 - "LiveReply"
Cohesion: 0.05
Nodes (13): _clamp(), clamp_spoken(), LiveReply, _plain_text(), speech_summary(), SpokenProse, strip_speak_tags(), ClampSpokenTests (+5 more)

### Community 35 - "auth_service.py"
Cohesion: 0.11
Nodes (6): AuthNotConfigured, BadCredentials, LockedOut, _now(), LockoutTests, LoginTests

### Community 37 - "__main__.py"
Cohesion: 0.15
Nodes (7): Config, _flag(), load_env_file(), _configure_logging(), main(), _run(), _task()

### Community 38 - "Project"
Cohesion: 0.06
Nodes (8): ProjectDao, Project, CodeService, ProjectService, CodeServiceTestCase, FakeConversationDao, FakeProjectDao, ProjectResolutionTests

### Community 39 - "asyncio"
Cohesion: 0.09
Nodes (14): list_people(), _callback_page(), create_mcp_server(), delete_mcp_server(), list_mcp_servers(), mcp_oauth_callback(), start_mcp_oauth(), update_mcp_server() (+6 more)

### Community 40 - "DATGlassesCamera"
Cohesion: 0.10
Nodes (3): failed, notReady, DATGlassesCamera

### Community 41 - "Sendable"
Cohesion: 0.07
Nodes (21): Phase, idle, listening, off, sentryBlocked, speaking, thinking, Cancellable (+13 more)

### Community 42 - "pending"
Cohesion: 0.22
Nodes (4): pending(), RecoverStuckTests, RunDueTests, RunTests

### Community 44 - "Responsibility"
Cohesion: 0.19
Nodes (4): Responsibility, at(), CheckForResponsibilitiesTests, DueTests

### Community 45 - "McpOAuthService"
Cohesion: 0.16
Nodes (6): _b64url(), McpOAuthService, _now(), _origin(), _parse_expiry(), _path()

### Community 46 - "make_update"
Cohesion: 0.16
Nodes (5): ConversationResolutionTests, make_update(), OpeningPromptTests, TwiMLTests, form()

### Community 47 - "build_service"
Cohesion: 0.07
Nodes (18): MeetingSegment, build_service(), ChunkingTests, CommitSegmentsTests, DeleteMeetingTests, FakeProjectDao, FinalizeTests, FollowUpTests (+10 more)

### Community 48 - "post"
Cohesion: 0.11
Nodes (15): adopt_claude_thread(), _authorized(), coding_socket(), coding_status(), get_coding_session(), list_claude_threads(), list_coding_sessions(), read_claude_thread() (+7 more)

### Community 49 - "call_controller.py"
Cohesion: 0.08
Nodes (16): answer_call(), call_status(), _escape(), mint_relay_token(), _opening_prompt(), relay_socket(), start_turn(), run_after_previous() (+8 more)

### Community 51 - "requests"
Cohesion: 0.18
Nodes (8): backend_url(), close_current_conversation(), fetch_conversation_info(), fetch_health(), fetch_projects(), fetch_tools(), stream_reply(), user_phone_number()

### Community 52 - "TurnTimer"
Cohesion: 0.13
Nodes (7): _build_file_logger(), _default_log_path(), _emit(), mark(), _timing_enabled(), TurnTimer, TurnTimerTests

### Community 53 - "auth_gate.py"
Cohesion: 0.16
Nodes (6): AuthGate, bearer_token(), _header(), is_exempt(), ExemptionTests, SidekickAuthTests

### Community 54 - "AuthService"
Cohesion: 0.12
Nodes (3): AuthService, _hash_token(), ConfigurationTests

### Community 55 - "run_migrations.py"
Cohesion: 0.16
Nodes (4): main(), migration_files(), _jsonable(), SQLService

### Community 56 - "build_service"
Cohesion: 0.15
Nodes (6): build_service(), CreateTests, FakeProjectDao, FakeUpdateService, ListAndCancelTests, soon()

### Community 57 - "FakeMessage"
Cohesion: 0.16
Nodes (10): fake_stream(), FakeMessage, FakeTextBlock, fake_stream(), fake_stream(), fake_stream(), StatusTextTests, fake_stream() (+2 more)

### Community 58 - "FakePersonaDao"
Cohesion: 0.14
Nodes (7): build_service(), CachingTests, FakePersonaDao, LoadingTests, seed_row(), ToolFacingWrapperTests, VersioningAndRollbackTests

### Community 59 - "ConversationLoopStreamTests"
Cohesion: 0.13
Nodes (4): ConversationLoopStreamTests, fake_stream(), fake_stream(), EventStreamTests

### Community 61 - "SpeechPlayer"
Cohesion: 0.07
Nodes (7): MP3StreamDecoder, PlaybackWatchdog, SpeechPlayer, .isBusy, .now, Stream, PlaybackWatchdogTests

### Community 62 - "EndpointDecisionTests"
Cohesion: 0.10
Nodes (5): endpoint_decision(), _endpoint_scale(), EndpointDecision, silence_budget_ms(), EndpointDecisionTests

### Community 63 - ".look"
Cohesion: 0.16
Nodes (11): Vision: "Hey Nova, what do you see?", Client → server, Connecting, Deviations from the brief and additions, Interjections, Prompt and tools, Server behaviour, Server → client (+3 more)

### Community 64 - "FakeCamera"
Cohesion: 0.21
Nodes (4): FakeCamera, FakeVision, settle(), VisionControllerTests

### Community 67 - "test_background_agent.py"
Cohesion: 0.17
Nodes (9): fake_get_response(), FakeConversationService, FakeMessage, FakeProjectDao, FakeTextBlock, FakeToolDao, FakeUpdateService, fake_get_response() (+1 more)

### Community 68 - "ServerEvent"
Cohesion: 0.03
Nodes (59): Note, PhotoSlot, AudioRole, final, progress, status, wake, CapturePurpose (+51 more)

### Community 70 - "Conversation"
Cohesion: 0.08
Nodes (5): ConversationDao, Conversation, ConversationClosedError, ConversationService, ThreadResolutionTests

### Community 71 - "nova_controller.py"
Cohesion: 0.05
Nodes (30): audio_file_bytes(), is_raw_pcm(), _pcm_params(), suffix_for_mime(), transcribe_serialized(), _canonical_wake_text(), chat_stream(), event_source() (+22 more)

### Community 74 - "TwilioService"
Cohesion: 0.09
Nodes (5): main(), report(), TwilioConfigurationError, TwilioService, ConfigurationGuardTests

### Community 76 - "AgentLoop"
Cohesion: 0.03
Nodes (14): AgentLoop, deliver(), mark_first_speech(), persist(), _memory_block_budget_seconds(), _PassHold, strip_expects_reply(), _strip_expects_reply_events() (+6 more)

### Community 77 - "faces_controller.py"
Cohesion: 0.16
Nodes (8): add_sample(), create_person(), delete_person(), _enroll(), DuplicatePerson, EnrollmentError, FaceModelsMissing, PersonNotFound

### Community 78 - ".durationMs"
Cohesion: 0.20
Nodes (4): PCMFormat, PreRollBuffer, .count, AudioFramingTests

### Community 79 - "re"
Cohesion: 0.11
Nodes (6): has_be_quiet_phrase(), _normalize(), parse_gate_reply(), SidekickGate, BeQuietPhraseTests, GateReplyTests

### Community 80 - "CameraError"
Cohesion: 0.14
Nodes (10): APIError, badResponse, .errorDescription, server, unauthorized, CameraError, .errorDescription, glassesAudioNotUp (+2 more)

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
Cohesion: 0.07
Nodes (3): SettingsService, ModelListTests, _ResetsSharedState

### Community 87 - "Person"
Cohesion: 0.11
Nodes (3): PersonDao, Person, FakePersonDao

### Community 88 - "test_sms.py"
Cohesion: 0.12
Nodes (7): BipConfigurationError, BipRequestError, is_permanent_bip_error(), normalize_phone_number(), _parse_number_list(), SmsRecipientError, NormalizationTests

### Community 89 - "test_responsibility_service.py"
Cohesion: 0.19
Nodes (4): build_service(), FakeProjectDao, FakeUpdateService, WindowTests

### Community 92 - "build_memory_service"
Cohesion: 0.10
Nodes (11): build_memory_service(), FakeConversationService, FakeEmbeddingService, FakeMemoryChunkDao, FakeMessage, FakeTextBlock, FakeToolDao, FakeUpdateService (+3 more)

### Community 93 - "meeting_service.py"
Cohesion: 0.04
Nodes (13): MeetingChunkDao, MeetingNotesDao, MeetingChunk, MeetingNotes, MeetingStatus, FakeAgentLoop, FakeChunkDao, FakeClaudeService (+5 more)

### Community 94 - "ASRService"
Cohesion: 0.06
Nodes (17): host_environment_prompt(), _host_kind(), _machine_line(), main(), ASRService, drop_hallucination(), _hotwords(), _load_parakeet() (+9 more)

### Community 96 - "UpdateService"
Cohesion: 0.08
Nodes (3): UpdateDao, Update, UpdateService

### Community 97 - "Mac code agent daemon"
Cohesion: 0.16
Nodes (14): Nova code agent (Mac) README, Anthropic API key stripping, Mac dials out design, Per-session git worktree, Known limits (awake Mac, bounded replay, cache cost), launchd install and menu app, Mac code agent daemon, NOVA_CODE_TOKEN shared secret (+6 more)

### Community 100 - "_FakeStream"
Cohesion: 0.18
Nodes (5): _drain(), _FakeMessage, _FakeStream, _FakeUsage, TurnStreamUsageMarkTests

### Community 101 - "._run_begin"
Cohesion: 0.29
Nodes (4): BeginFlowTests, fake_get(), fake_post(), FakeResponse

### Community 104 - "Keys"
Cohesion: 0.08
Nodes (23): Keys, assistantText, bytes, chunkBase64, client, code, conversationId, count (+15 more)

### Community 105 - "FaceService"
Cohesion: 0.13
Nodes (4): FaceService, match(), _normalise(), FacesRoutesTests

### Community 106 - "typing"
Cohesion: 0.07
Nodes (9): BaseDao, MemoryChunkDao, MessageDao, MemoryChunk, MemoryMatch, Message, MessageRole, FakeClaudeResponse (+1 more)

### Community 108 - "VoiceMode"
Cohesion: 0.26
Nodes (4): VoiceMode, conversation, sentry, VoiceModeStore

### Community 110 - "service/__init__.py"
Cohesion: 0.12
Nodes (4): DeployService, HealthTimeoutTests, CheckDeployStatusTests, DeployMainTests

### Community 111 - "FakeDao"
Cohesion: 0.17
Nodes (6): fake_post(), CompleteAndRefreshTests, fake_post(), ConnectorFilteringTests, FakeDao, oauth_server()

### Community 112 - "MemoryInjectionTests"
Cohesion: 0.20
Nodes (4): MemoryInjectionTests, boom(), notification(), PendingNotificationsInjectionTests

### Community 113 - "sessions.py"
Cohesion: 0.15
Nodes (7): _contained(), make_guard(), can_use_tool(), _as_int(), _ms_to_iso(), health(), root()

### Community 114 - "AppModel"
Cohesion: 0.05
Nodes (24): ImageIO, AppModel, .serverURLString, NovaGlassesApp, .body, RootView, .body, AuthStore (+16 more)

### Community 115 - "asr-bench.py"
Cohesion: 0.36
Nodes (4): cut_clips(), default_audio(), load(), main()

### Community 117 - ".create_person"
Cohesion: 0.18
Nodes (5): GalleryPerson, face_row(), FaceServiceTests, MatchTests, unit()

### Community 119 - "Foundation"
Cohesion: 0.07
Nodes (12): AudioToolbox, AVFoundation, Foundation, AudioSessionPolicy, SpeechWakeDetector, .isAvailable, MWDATCamera, MWDATCore (+4 more)

### Community 120 - "Earcon"
Cohesion: 0.13
Nodes (14): Earcons, Earcon, cancel, done, error, shutter, sidekickCue, sidekickOff (+6 more)

### Community 121 - "SidekickSocketTests"
Cohesion: 0.15
Nodes (3): GateDecision, SidekickService, SidekickSocketTests

### Community 125 - "worker.py"
Cohesion: 0.16
Nodes (10): BuildJobsTests, build_jobs(), _recover_stuck_tasks(), _run_check_for_responsibilities(), _run_check_for_stale_conversations(), _run_deliver_pending_updates(), _run_process_conversations(), _run_scheduled_tasks() (+2 more)

### Community 126 - "SidekickController"
Cohesion: 0.12
Nodes (9): ConversationIdStore, EarconPlaying, GlassesCamera, MainScheduler, NovaSocketing, Scheduling, SpeechPlaying, VisionUploading (+1 more)

### Community 127 - "test_deploy_main.py"
Cohesion: 0.11
Nodes (7): DryRunTests, FailingTestsAbortTests, HappyPathTests, RollbackPathTests, _runner(), _silent_logger(), StopPidIsNeverATreeKillTests

### Community 128 - "agent_loop.py"
Cohesion: 0.07
Nodes (9): PromptSourceEnum, _comparable(), is_repeat(), GlassesPromptSourceTests, ConversationTurnMcpDisabledReplayTests, FakeConversationService, FakeMcpService, FakeToolDao (+1 more)

### Community 130 - "FakeDao"
Cohesion: 0.08
Nodes (5): GateTestCase, WebSocketGateTests, AuthenticateTests, AuthServiceTestCase, FakeDao

### Community 132 - "build_app"
Cohesion: 0.22
Nodes (3): build_app(), stream(), fake_stream()

### Community 135 - "history_compaction.py"
Cohesion: 0.20
Nodes (15): _block_chars(), cap_messages(), clear_old_tool_results(), _clearable_blocks(), compact_history(), _env_int(), _is_plain_user_turn(), _history() (+7 more)

### Community 137 - "SidekickConnection"
Cohesion: 0.17
Nodes (3): Utterances, sidekick_socket(), SidekickConnection

### Community 139 - ".add"
Cohesion: 0.14
Nodes (6): AudioLog, Entry, AudioRouteManager, Route, .summary, .body

### Community 141 - "NovaGlasses"
Cohesion: 0.29
Nodes (6): Build and test (CLI), Code map, How it behaves, Install on your iPhone, NovaGlasses, On-device field checklist

### Community 144 - "ImageStore"
Cohesion: 0.14
Nodes (5): ImageStore, _in_view_text(), VisionImage, ContentBlocksTests, ImageStoreTests

### Community 149 - "TwilioErrorClassificationTests"
Cohesion: 0.15
Nodes (6): describe_twilio_error(), is_permanent_twilio_error(), SimpleNamespace_Exception, TwilioErrorClassificationTests, reject(), flake()

### Community 153 - "VisionService"
Cohesion: 0.12
Nodes (3): is_image_block(), VisionService, LookToolTests

### Community 154 - "TurnStream"
Cohesion: 0.07
Nodes (14): ToolUseStarted, TurnStream, PrefetchedConversationTests, fake_stream(), fake_stream(), TurnStreamTests, __iter__(), get_final_message() (+6 more)

### Community 155 - "MemoryChunkService"
Cohesion: 0.07
Nodes (5): EmbeddingService, MemoryChunkService, ParseChunksTests, SplitTranscriptTests, RetrievableQueryTests

### Community 156 - "test_process_supervisor.py"
Cohesion: 0.13
Nodes (4): fetch(), main(), sha256(), MirrorTests

### Community 158 - "test_sidekick.py"
Cohesion: 0.08
Nodes (12): is_sidekick_pass(), _agent_loop(), FakeConversationService, FakeMessage, FakeTextBlock, FakeToolDao, FakeToolUseBlock, _live() (+4 more)

### Community 159 - "Rig"
Cohesion: 0.18
Nodes (3): Rig, SidekickControllerTests, SidekickEventCodingTests

### Community 161 - "auth_controller.py"
Cohesion: 0.19
Nodes (6): _client_ip(), current_session(), list_sessions(), login(), logout(), logout_all()

### Community 165 - "settings_controller.py"
Cohesion: 0.11
Nodes (6): get_all_settings(), get_available_models(), get_claude_credits(), ModelSwitchRequest, set_model(), ClaudeCreditsService

### Community 170 - "subprocess"
Cohesion: 0.22
Nodes (7): create(), _git(), remove(), resolve_repo(), slugify(), Workspace, WorktreeError

### Community 172 - "FakeHttp"
Cohesion: 0.25
Nodes (4): build_service(), FakeHttp, InfobipRequestTests, SendSmsTests

### Community 173 - "CommandLineService"
Cohesion: 0.07
Nodes (3): CommandLineService, BackgroundTests, ForegroundTests

### Community 176 - "dict"
Cohesion: 0.25
Nodes (3): basic(), InboundSecretTests, RecipientAllowlistTests

### Community 177 - "VisionRoutesTests"
Cohesion: 0.26
Nodes (3): Identification, FakeFaceService, VisionRoutesTests

### Community 181 - "AddPersonView"
Cohesion: 0.24
Nodes (6): .api, AddPersonView, .body, FacesView, .body, PhotosUI

### Community 183 - ".setUp"
Cohesion: 0.12
Nodes (4): DirectTurnCounterTests, fake_transcribe(), FakeGate, FakeSidekickLoop

### Community 186 - "replay_request.py"
Cohesion: 0.20
Nodes (5): main(), one_call(), main(), one_call(), variants()

### Community 190 - "unittest"
Cohesion: 0.10
Nodes (4): DeliveryStatus, ReportType, EscapingTests, HostEnvironmentPromptTests

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
Nodes (3): FakeToolUseBlock, InterruptedToolCallTests, fake_stream()

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
Cohesion: 0.13
Nodes (4): _allowed_origins(), lifespan(), _broadcast(), face_socket()

## Ambiguous Edges - Review These
- `TTS conversion enhancer prompt (empty)` → `Voice mode tone guidelines`  [AMBIGUOUS]
  prompting/tts_conversion_enhancer_prompt.txt · relation: conceptually_related_to

## Knowledge Gaps
- **165 isolated node(s):** `UserNotifications`, `.serverURLString`, `.summary`, `AudioToolbox`, `.count` (+160 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1622 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **73 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `TTS conversion enhancer prompt (empty)` and `Voice mode tone guidelines`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `NovaGlasses` connect `NovaGlasses` to `SentryModeTests`, `ConversationController`, `.look`?**
  _High betweenness centrality (0.310) - this node is a cross-community bridge._
- **Are the 43 inferred relationships involving `AgentLoop` (e.g. with `Server behaviour` and `PromptEnums`) actually correct?**
  _`AgentLoop` has 43 INFERRED edges - model-reasoned connections that need verification._
- **What connects `UserNotifications`, `.serverURLString`, `.summary` to the rest of the system?**
  _165 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Tool` be split into smaller, more focused modules?**
  _Cohesion score 0.11711711711711711 - nodes in this community are weakly interconnected._
- **Why does `Vision: "Hey Nova, what do you see?"` connect `.look` to `NovaGlasses`?**
  _High betweenness centrality (0.310) - this node is a cross-community bridge._
- **Are the 21 inferred relationships involving `Conversation` (e.g. with `_is_stale()` and `ConversationDao`) actually correct?**
  _`Conversation` has 21 INFERRED edges - model-reasoned connections that need verification._