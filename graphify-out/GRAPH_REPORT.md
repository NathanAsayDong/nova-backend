# Graph Report - nova-backend  (2026-11-10)

## Corpus Check
- 234 files · ~204,689 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: (none) 3, .mdc 1, .pbxproj 1)

## Summary
- 5064 nodes · 11882 edges · 229 communities (141 shown, 88 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 1272 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `6d3d876e`
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
- MemoryChunkService
- Harness
- CodingService
- ScheduledTaskService
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
- ElevenLabsService
- _install_fake_modules
- test_auth_service.py
- LiveReply
- auth_controller.py
- SessionManager
- __main__.py
- VisionService
- test_meeting_service.py
- DATGlassesCamera
- .get_current_time
- build_service
- ResponsibilityService
- Responsibility
- McpOAuthService
- make_update
- build_service
- pathlib
- call_controller.py
- McpServerService
- HomeView
- TurnTimer
- test_auth_gate.py
- AuthService
- Project
- TwilioErrorClassificationTests
- FakeMessage
- FakePersonaDao
- ConversationLoopStreamTests
- ConversationClosedError
- SpeechPlayer
- EndpointDecisionTests
- ImageStore
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
- parse_gate_reply
- SidekickController
- fake_stream
- LiveScreenTests
- FakeMcpServerDao
- FakeMeetingDao
- CrudTests
- SettingsService
- Person
- bip_service.py
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
- update_delivery_service.py
- NovaSocket
- Keys
- FaceService
- .after
- audio_ws.py
- ConversationIdStore
- .repair_tool_pairing
- test_asr_filters.py
- FakeDao
- MemoryInjectionTests
- sessions.py
- AppModel
- MeetingNotes
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
- String
- Qwen3-TTS: Nova's local TTS fallback
- agent_loop.py
- ._to_dict
- FakeDao
- ClassificationTests
- CapturePurpose
- CaptureEngine
- history_compaction.py
- ToolService
- SidekickConnection
- WorkingTreeTests
- AudioRouteManager
- .isOnlyWakePhrase
- run_migrations.py
- SpokenProse
- TTSService
- RelayTokenTests
- SpeechWakeDetector
- AuthenticateTests
- clamp_spoken
- PerformTests
- speech_summary
- .iter_sentence_chunks
- GoodbyeTimingTests
- FakeConversationService
- .conversation_loop_events
- WakeDetecting
- auth_service.py
- FallbackChainTests
- PassSentinelTests
- Rig
- CLAUDE.md
- asyncio
- install.sh
- uninstall.sh
- settings_controller.py
- nova-backend
- QwenTTSService
- CurrentModelTests
- test_sms.py
- CommandLineService
- DemoService
- CooldownTests
- match
- VisionRoutesTests
- AuthStore
- prepare
- os
- AddPersonView
- PersonaPrompt
- .setUp
- get_conversation_messages
- .look
- replay_request.py
- .wantsToSee
- ._service
- GlassesSocketTests
- requests
- MacSessionLifecycleTests
- XCTestCase
- ClaudeCreditsService
- SentryModeTests
- CreateScheduleRequirementTests
- InterruptedToolCallTests
- post
- Entry
- ThinkingPulseTests
- test_persona_service.py
- meeting_service.py
- split_wake_phrase
- test_settings_service.py
- iter_in_thread
- _said
- AgentLink
- _FakeTable
- shell.py
- FakeConversationService
- FinishedSessionTowerTests
- HostEnvironmentPromptTests
- FallbackTests
- .split_sms_body
- TranscribeUtteranceTests
- GlassesCannotRecordMeetingsTests
- Phase
- VisionClient
- _PassHold
- SidekickService
- MirrorTests
- main.py
- SocketConnectionState
- get_nova_state
- FakeAgentLoop
- ReplyQueue

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
- `What wasn't verified` --references--> `_generate_pcm_chunks()`  [INFERRED]
  docs/QWEN_TTS.md → src/service/qwen_tts_service.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Remote access path: Firebase frontend to Cloudflare Tunnel to tower API** — docs_hosting_firebase_hosting, docs_hosting_cloudflare_tunnel, docs_hosting_tower_api [EXTRACTED 0.95]
- **Mac agent core design principles** — mac_agent_readme_dial_out, mac_agent_readme_sessions_as_threads, mac_agent_readme_git_worktree [EXTRACTED 1.00]
- **Persisted-action safety rules across foreground and background agents** — prompting_nova_persona_prompt_confirm_persisted_actions, prompting_nova_persona_prompt_clarify_before_executing, prompting_background_agent_prompt_no_outward_actions [INFERRED 0.85]

## Communities (229 total, 88 thin omitted)

### Community 0 - "Tool"
Cohesion: 0.13
Nodes (5): list_tools(), ToolDao, Tool, FakeToolDao, ToolServiceTests

### Community 1 - "sms_controller.py"
Cohesion: 0.16
Nodes (8): _authorize(), _handle_inbound(), inbound_sms(), inbound_sms_with_path_token(), _is_stale(), _receive(), resolve_sms_conversation(), _run_sms_turn()

### Community 2 - "SimpleFinancesService"
Cohesion: 0.11
Nodes (6): SimplApiError, SimplConfigurationError, SimpleFinancesService, response(), SimpleFinancesServiceTest, SimplFinancesToolRegistrationTest

### Community 3 - "text"
Cohesion: 0.10
Nodes (9): _artifact_for(), encode(), _truncate(), ToolUseStarted, AuthenticationTests, forward(), PathTokenRouteTests, SenderGateTests (+1 more)

### Community 5 - "test_openai_loop.py"
Cohesion: 0.17
Nodes (7): FakeClient, FakeFunctionCall, FakeResponse, FakeResponsesAPI, FakeTool, FakeToolService, OpenAILoopTests

### Community 6 - "Rig"
Cohesion: 0.10
Nodes (8): FakePlayer, .isBusy, FakeSocket, .starts, FakeWake, Item, ManualScheduler, Rig

### Community 7 - "AgentLoopImageTests"
Cohesion: 0.16
Nodes (6): AgentLoopImageTests, fake_stream(), FakeConversationService, FakeMessage, FakeTextBlock, FakeToolUseBlock

### Community 8 - ".run_agent"
Cohesion: 0.07
Nodes (11): BackgroundAgentTests, fake_get_response(), FakeConversationService, FakeMessage, FakeTextBlock, FakeToolDao, FakeUpdateService, ReportTypeTests (+3 more)

### Community 9 - "._env"
Cohesion: 0.14
Nodes (3): CartesiaService, CartesiaRequestTests, ProviderSelectionTests

### Community 10 - "make_update"
Cohesion: 0.14
Nodes (11): at(), BadgeOnlyTests, build_service(), CallDeliveryTests, EmailDeliveryTests, make_update(), QuietHoursTests, SettleCallTests (+3 more)

### Community 11 - "ClaudeService"
Cohesion: 0.10
Nodes (4): ClaudeService, _maybe_print_prompt(), GenerationKwargsTests, ClaudeServiceMcpKwargsTests

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
Cohesion: 0.05
Nodes (7): MemoryChunkDao, MemoryChunk, MemoryMatch, EmbeddingService, MemoryChunkService, ParseChunksTests, RetrievableQueryTests

### Community 17 - "Harness"
Cohesion: 0.08
Nodes (19): LevelSmoother, Snapshot, State, calibrating, cooldown, idle, onset, speaking (+11 more)

### Community 19 - "ScheduledTaskService"
Cohesion: 0.09
Nodes (4): ScheduledTaskDao, ScheduledTask, TaskStatus, ScheduledTaskService

### Community 20 - "_most_recent_local_midnight_utc"
Cohesion: 0.07
Nodes (7): _most_recent_local_midnight_utc(), IsIdleTests, IsPastRolloverTests, build_service(), CheckForStaleConversationsTests, FakeConversationDao, MostRecentLocalMidnightUtcTests

### Community 21 - "json"
Cohesion: 0.16
Nodes (16): _all(), await_ready(), check(), _entry(), kill_tree(), _log_paths(), pid_alive(), port_open() (+8 more)

### Community 22 - "process_supervisor.py"
Cohesion: 0.07
Nodes (25): create(), _git(), remove(), resolve_repo(), slugify(), Workspace, WorktreeError, _all() (+17 more)

### Community 23 - "build_service"
Cohesion: 0.07
Nodes (11): build_service(), FakeClaudeService, FakeConversationService, FakeEmbeddingService, FakeMemoryChunkDao, FetchMemoryTests, ProcessConversationsTests, boom() (+3 more)

### Community 24 - "MeetingError"
Cohesion: 0.09
Nodes (19): transcribe_segments_serialized(), delete_meeting(), get_active_meeting(), get_meeting(), get_meeting_segments(), list_meetings(), _meeting_error(), meeting_socket() (+11 more)

### Community 25 - "CursorService"
Cohesion: 0.17
Nodes (4): CursorService, CursorServiceError, CursorServiceTests, _FakeResponse

### Community 26 - "MeetingService"
Cohesion: 0.06
Nodes (3): MeetingDao, Meeting, MeetingService

### Community 27 - "FileOperationTests"
Cohesion: 0.09
Nodes (3): EditTests, FileOperationTests, PathContainmentTests

### Community 28 - "CodingSession"
Cohesion: 0.15
Nodes (4): CodingSessionDao, CodingEvent, CodingSession, CodingStatus

### Community 29 - "Update"
Cohesion: 0.07
Nodes (5): UpdateDao, DeliveryStatus, Update, UpdateDeliveryService, UpdateService

### Community 30 - "ConversationController"
Cohesion: 0.15
Nodes (6): ConversationController, .idleMessage, .isEnabled, .isWorking, .wakeWatching, Sentry mode

### Community 32 - "_install_fake_modules"
Cohesion: 0.12
Nodes (6): _FakeTorch, _full_chain_env(), _install_fake_modules(), QwenTTSCooldownTests, QwenTTSProviderSelectionTests, _raise_for_torch()

### Community 33 - "test_auth_service.py"
Cohesion: 0.10
Nodes (4): NovaSessionDao, row_to_session(), NovaSession, RowConversionTests

### Community 35 - "auth_controller.py"
Cohesion: 0.11
Nodes (9): _client_ip(), current_session(), list_sessions(), login(), logout(), AuthNotConfigured, BadCredentials, LockedOut (+1 more)

### Community 36 - "SessionManager"
Cohesion: 0.12
Nodes (5): _as_int(), _flatten(), _ms_to_iso(), Session, SessionManager

### Community 37 - "__main__.py"
Cohesion: 0.12
Nodes (8): Config, _flag(), load_env_file(), Link, _configure_logging(), main(), _run(), _task()

### Community 38 - "VisionService"
Cohesion: 0.12
Nodes (3): is_image_block(), VisionService, LookToolTests

### Community 39 - "test_meeting_service.py"
Cohesion: 0.06
Nodes (11): MeetingSegment, ChunkingTests, FakeChunkDao, FakeClaudeService, FakeConversationDao, FakeEmbeddingService, FakeNotesDao, FakeUpdateService (+3 more)

### Community 40 - "DATGlassesCamera"
Cohesion: 0.07
Nodes (15): CameraError, .errorDescription, failed, glassesAudioNotUp, noCamera, notReady, timeout, DATGlassesCamera (+7 more)

### Community 42 - "build_service"
Cohesion: 0.15
Nodes (6): build_service(), CreateTests, FakeProjectDao, FakeUpdateService, ListAndCancelTests, soon()

### Community 44 - "Responsibility"
Cohesion: 0.15
Nodes (5): Responsibility, at(), CheckForResponsibilitiesTests, DueTests, ReportMediumTests

### Community 45 - "McpOAuthService"
Cohesion: 0.18
Nodes (5): McpOAuthService, _now(), _origin(), _path(), CompleteAndRefreshTests

### Community 46 - "make_update"
Cohesion: 0.16
Nodes (5): ConversationResolutionTests, make_update(), OpeningPromptTests, TwiMLTests, form()

### Community 47 - "build_service"
Cohesion: 0.08
Nodes (13): build_service(), CommitSegmentsTests, DeleteMeetingTests, FakeProjectDao, FollowUpTests, explode(), NotesTests, recording_meeting() (+5 more)

### Community 48 - "pathlib"
Cohesion: 0.18
Nodes (8): main(), _hotwords(), _load_parakeet(), missing_cuda_libraries(), _nvidia_wheel_dll_dirs(), _platform_default_provider(), _resolve_whisper_device(), _setup_cuda_libraries()

### Community 49 - "call_controller.py"
Cohesion: 0.10
Nodes (15): answer_call(), call_status(), _escape(), mint_relay_token(), _opening_prompt(), relay_socket(), start_turn(), run_after_previous() (+7 more)

### Community 51 - "HomeView"
Cohesion: 0.11
Nodes (13): NovaGlassesApp, .body, RootView, AudioLogView, HomeView, .cameraText, .connectionText, .controller (+5 more)

### Community 52 - "TurnTimer"
Cohesion: 0.10
Nodes (8): _emit(), TurnTimer, _drain(), _FakeMessage, _FakeStream, _FakeUsage, TurnStreamUsageMarkTests, TurnTimerTests

### Community 53 - "test_auth_gate.py"
Cohesion: 0.11
Nodes (7): AuthGate, bearer_token(), _header(), is_exempt(), build_app(), ExemptionTests, SidekickAuthTests

### Community 55 - "Project"
Cohesion: 0.06
Nodes (7): Project, CodeService, ProjectService, CodeServiceTestCase, FakeConversationDao, FakeProjectDao, ProjectResolutionTests

### Community 56 - "TwilioErrorClassificationTests"
Cohesion: 0.15
Nodes (6): describe_twilio_error(), is_permanent_twilio_error(), SimpleNamespace_Exception, TwilioErrorClassificationTests, reject(), flake()

### Community 57 - "FakeMessage"
Cohesion: 0.10
Nodes (15): fake_stream(), FakeMessage, FakeTextBlock, fake_stream(), fake_stream(), fake_stream(), fake_stream(), fake_stream() (+7 more)

### Community 58 - "FakePersonaDao"
Cohesion: 0.13
Nodes (7): build_service(), CachingTests, FakePersonaDao, LoadingTests, seed_row(), ToolFacingWrapperTests, VersioningAndRollbackTests

### Community 59 - "ConversationLoopStreamTests"
Cohesion: 0.13
Nodes (4): ConversationLoopStreamTests, fake_stream(), fake_stream(), EventStreamTests

### Community 61 - "SpeechPlayer"
Cohesion: 0.07
Nodes (7): MP3StreamDecoder, PlaybackWatchdog, SpeechPlayer, .isBusy, .now, Stream, PlaybackWatchdogTests

### Community 62 - "EndpointDecisionTests"
Cohesion: 0.11
Nodes (4): endpoint_decision(), EndpointDecision, silence_budget_ms(), EndpointDecisionTests

### Community 63 - "ImageStore"
Cohesion: 0.14
Nodes (5): ImageStore, _in_view_text(), VisionImage, ContentBlocksTests, ImageStoreTests

### Community 64 - "FakeCamera"
Cohesion: 0.21
Nodes (4): FakeCamera, FakeVision, settle(), VisionControllerTests

### Community 67 - "test_spoken_reply.py"
Cohesion: 0.19
Nodes (5): _comparable(), is_repeat(), strip_speak_tags(), IsRepeatTests, StripSpeakTagsTests

### Community 68 - "ClientEvent"
Cohesion: 0.08
Nodes (21): AudioRole, final, progress, status, wake, ClientEvent, abort, interrupted (+13 more)

### Community 70 - "Conversation"
Cohesion: 0.07
Nodes (7): ConversationDao, Conversation, Message, ConversationService, FakeConversationService, FakeConversationService, ThreadResolutionTests

### Community 71 - "nova_controller.py"
Cohesion: 0.14
Nodes (12): parse_conversation_id(), parse_image_ids(), _partial_is_due(), resolve_chat_request(), send_assistant_text(), _send_locked(), _speculative_asr_enabled(), stream_tts_audio() (+4 more)

### Community 72 - "McpServer"
Cohesion: 0.21
Nodes (3): McpServer, _b64url(), _parse_expiry()

### Community 74 - "TwilioService"
Cohesion: 0.09
Nodes (5): main(), report(), TwilioConfigurationError, TwilioService, ConfigurationGuardTests

### Community 76 - "AgentLoop"
Cohesion: 0.04
Nodes (8): PromptSourceEnum, AgentLoop, persist(), _memory_block_budget_seconds(), strip_expects_reply(), _strip_expects_reply_events(), GlassesPromptSourceTests, SanitizeMcpHistoryTests

### Community 77 - "faces_controller.py"
Cohesion: 0.11
Nodes (11): add_sample(), create_person(), delete_person(), _enroll(), read_jpeg_body(), upload_image(), DuplicatePerson, EnrollmentError (+3 more)

### Community 78 - ".durationMs"
Cohesion: 0.19
Nodes (4): PCMFormat, PreRollBuffer, .count, AudioFramingTests

### Community 79 - "parse_gate_reply"
Cohesion: 0.18
Nodes (3): parse_gate_reply(), SidekickGate, GateReplyTests

### Community 80 - "SidekickController"
Cohesion: 0.18
Nodes (9): Cancellable, EarconPlaying, GlassesCamera, MainScheduler, NovaSocketing, Scheduling, SpeechPlaying, VisionUploading (+1 more)

### Community 81 - "fake_stream"
Cohesion: 0.10
Nodes (6): fake_stream(), FailureHistoryAndRetryTests, fake_stream(), fake_stream(), _FakeBadRequestError, SpokenTrackTests

### Community 82 - "LiveScreenTests"
Cohesion: 0.12
Nodes (4): LiveScreenTests, ScriptedTurnStream, get_final_message(), __iter__()

### Community 83 - "FakeMcpServerDao"
Cohesion: 0.17
Nodes (3): build_service(), FakeMcpServerDao, McpServerServiceTests

### Community 87 - "Person"
Cohesion: 0.11
Nodes (3): PersonDao, Person, FakePersonDao

### Community 88 - "bip_service.py"
Cohesion: 0.08
Nodes (8): BipConfigurationError, BipRequestError, _describe_response_error(), is_permanent_bip_error(), normalize_phone_number(), _parse_number_list(), SmsRecipientError, NormalizationTests

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

### Community 94 - "ASRService"
Cohesion: 0.11
Nodes (6): cut_clips(), default_audio(), load(), main(), ASRService, TranscriptSegment

### Community 96 - "pending"
Cohesion: 0.22
Nodes (4): pending(), RecoverStuckTests, RunDueTests, RunTests

### Community 97 - "Mac code agent daemon"
Cohesion: 0.16
Nodes (14): Nova code agent (Mac) README, Anthropic API key stripping, Mac dials out design, Per-session git worktree, Known limits (awake Mac, bounded replay, cache cost), launchd install and menu app, Mac code agent daemon, NOVA_CODE_TOKEN shared secret (+6 more)

### Community 101 - "._run_begin"
Cohesion: 0.23
Nodes (6): BeginFlowTests, fake_get(), fake_post(), fake_post(), fake_post(), FakeResponse

### Community 102 - "update_delivery_service.py"
Cohesion: 0.09
Nodes (3): user_phone_number(), EmailService, _env_int()

### Community 104 - "Keys"
Cohesion: 0.08
Nodes (23): Keys, assistantText, bytes, chunkBase64, client, code, conversationId, count (+15 more)

### Community 105 - "FaceService"
Cohesion: 0.16
Nodes (3): FaceService, _normalise(), FacesRoutesTests

### Community 107 - "audio_ws.py"
Cohesion: 0.17
Nodes (8): audio_file_bytes(), is_raw_pcm(), _pcm_params(), suffix_for_mime(), transcribe_serialized(), emit_partial_transcript(), run_speculative_transcription(), AudioFileBytesTests

### Community 108 - "ConversationIdStore"
Cohesion: 0.18
Nodes (5): ConversationIdStore, VoiceMode, conversation, sentry, VoiceModeStore

### Community 110 - "test_asr_filters.py"
Cohesion: 0.26
Nodes (4): drop_hallucination(), DropHallucinationTests, _segment(), WhisperSegmentFilterTests

### Community 111 - "FakeDao"
Cohesion: 0.23
Nodes (3): ConnectorFilteringTests, FakeDao, oauth_server()

### Community 112 - "MemoryInjectionTests"
Cohesion: 0.20
Nodes (5): FakeMessage, FakeTextBlock, FakeToolDao, MemoryInjectionTests, fake_stream()

### Community 113 - "sessions.py"
Cohesion: 0.23
Nodes (4): _contained(), make_guard(), can_use_tool(), _is_prose()

### Community 114 - "AppModel"
Cohesion: 0.13
Nodes (6): AppModel, .serverURLString, .body, .body, LoginView, .body

### Community 115 - "MeetingNotes"
Cohesion: 0.15
Nodes (3): MeetingNotesDao, MeetingChunk, MeetingNotes

### Community 117 - "host_environment_prompt.py"
Cohesion: 0.24
Nodes (4): host_environment_prompt(), _host_kind(), _machine_line(), _env_flag()

### Community 118 - "APIClient"
Cohesion: 0.16
Nodes (7): APIClient, APIError, badResponse, .errorDescription, server, unauthorized, Person

### Community 119 - "Foundation"
Cohesion: 0.11
Nodes (11): AudioToolbox, AVFoundation, Foundation, ImageIO, AudioSessionPolicy, MWDATCamera, MWDATCore, Observation (+3 more)

### Community 120 - "Earcon"
Cohesion: 0.12
Nodes (15): Earcons, Note, Earcon, cancel, done, error, shutter, sidekickCue (+7 more)

### Community 125 - "worker.py"
Cohesion: 0.16
Nodes (10): BuildJobsTests, build_jobs(), _recover_stuck_tasks(), _run_check_for_responsibilities(), _run_check_for_stale_conversations(), _run_deliver_pending_updates(), _run_process_conversations(), _run_scheduled_tasks() (+2 more)

### Community 127 - "Qwen3-TTS: Nova's local TTS fallback"
Cohesion: 0.14
Nodes (12): CustomVoice, not Base, Env vars, Install (Windows tower), Qwen3-TTS: Nova's local TTS fallback, Smoke test, What wasn't verified, Why it's here, _generate_pcm_chunks() (+4 more)

### Community 128 - "agent_loop.py"
Cohesion: 0.09
Nodes (7): MessageRole, TurnStream, ToolExecutionError, FakeProjectDao, ConversationTurnMcpDisabledReplayTests, FakeClaudeResponse, FakeTextBlock

### Community 130 - "FakeDao"
Cohesion: 0.14
Nodes (3): GateTestCase, WebSocketGateTests, FakeDao

### Community 132 - "CapturePurpose"
Cohesion: 0.17
Nodes (5): Capture, CapturePurpose, sentry, turn, wakeCheck

### Community 135 - "history_compaction.py"
Cohesion: 0.20
Nodes (15): _block_chars(), cap_messages(), clear_old_tool_results(), _clearable_blocks(), compact_history(), _env_int(), _is_plain_user_turn(), _history() (+7 more)

### Community 136 - "ToolService"
Cohesion: 0.25
Nodes (4): main(), main(), main(), ToolService

### Community 137 - "SidekickConnection"
Cohesion: 0.17
Nodes (3): Utterances, sidekick_socket(), SidekickConnection

### Community 139 - "AudioRouteManager"
Cohesion: 0.22
Nodes (3): AudioRouteManager, Route, .summary

### Community 141 - "run_migrations.py"
Cohesion: 0.19
Nodes (4): main(), migration_files(), _jsonable(), SQLService

### Community 147 - "AuthenticateTests"
Cohesion: 0.12
Nodes (3): AuthenticateTests, AuthServiceTestCase, LoginTests

### Community 148 - "clamp_spoken"
Cohesion: 0.23
Nodes (5): deliver(), mark_first_speech(), _clamp(), clamp_spoken(), ClampSpokenTests

### Community 153 - "FakeConversationService"
Cohesion: 0.17
Nodes (3): CountingService, FakeConversationService, FakeToolDao

### Community 154 - ".conversation_loop_events"
Cohesion: 0.18
Nodes (7): PrefetchedConversationTests, AgentLoopMcpTests, fake_stream(), fake_stream(), fake_stream(), FakeBlock, FakeMessage

### Community 155 - "WakeDetecting"
Cohesion: 0.17
Nodes (7): WakeDetecting, Build and test (CLI), Code map, How it behaves, Install on your iPhone, NovaGlasses, On-device field checklist

### Community 156 - "auth_service.py"
Cohesion: 0.18
Nodes (5): fetch(), main(), sha256(), _hash_token(), _now()

### Community 158 - "PassSentinelTests"
Cohesion: 0.09
Nodes (11): is_sidekick_pass(), _agent_loop(), FakeMessage, FakeTextBlock, FakeToolDao, FakeToolUseBlock, _live(), get_final_message() (+3 more)

### Community 159 - "Rig"
Cohesion: 0.18
Nodes (3): Rig, SidekickControllerTests, SidekickEventCodingTests

### Community 161 - "asyncio"
Cohesion: 0.09
Nodes (14): list_people(), _callback_page(), create_mcp_server(), delete_mcp_server(), list_mcp_servers(), mcp_oauth_callback(), start_mcp_oauth(), update_mcp_server() (+6 more)

### Community 165 - "settings_controller.py"
Cohesion: 0.19
Nodes (4): get_all_settings(), get_available_models(), ModelSwitchRequest, set_model()

### Community 170 - "QwenTTSService"
Cohesion: 0.23
Nodes (3): QwenTTSService, _qwen(), QwenTTSGenerationTests

### Community 172 - "test_sms.py"
Cohesion: 0.10
Nodes (10): BipService, basic(), build_service(), FakeHttp, FakeResponse, InboundSecretTests, InfobipRequestTests, RecipientAllowlistTests (+2 more)

### Community 173 - "CommandLineService"
Cohesion: 0.07
Nodes (3): CommandLineService, BackgroundTests, ForegroundTests

### Community 176 - "match"
Cohesion: 0.16
Nodes (6): GalleryPerson, match(), face_row(), FaceServiceTests, MatchTests, unit()

### Community 177 - "VisionRoutesTests"
Cohesion: 0.26
Nodes (3): Identification, FakeFaceService, VisionRoutesTests

### Community 178 - "AuthStore"
Cohesion: 0.27
Nodes (3): AuthStore, .baseQuery, Security

### Community 179 - "prepare"
Cohesion: 0.27
Nodes (4): prepare(), jpeg(), phone(), PrepareTests

### Community 180 - "os"
Cohesion: 0.04
Nodes (23): _remove(), transcribe_utterance(), _build_file_logger(), _default_log_path(), mark(), _timing_enabled(), _describe_failure(), _env_flag() (+15 more)

### Community 181 - "AddPersonView"
Cohesion: 0.16
Nodes (7): .api, ImagePrep, AddPersonView, .body, FacesView, .body, PhotosUI

### Community 183 - ".setUp"
Cohesion: 0.12
Nodes (4): DirectTurnCounterTests, fake_transcribe(), FakeGate, FakeSidekickLoop

### Community 184 - "get_conversation_messages"
Cohesion: 0.24
Nodes (5): close_conversation(), get_conversation(), get_conversation_messages(), _parse_uuid(), _project_payload()

### Community 185 - ".look"
Cohesion: 0.16
Nodes (11): Vision: "Hey Nova, what do you see?", Client → server, Connecting, Deviations from the brief and additions, Interjections, Prompt and tools, Server behaviour, Server → client (+3 more)

### Community 186 - "replay_request.py"
Cohesion: 0.20
Nodes (5): main(), one_call(), main(), one_call(), variants()

### Community 190 - "requests"
Cohesion: 0.27
Nodes (7): backend_url(), close_current_conversation(), fetch_conversation_info(), fetch_health(), fetch_projects(), fetch_tools(), stream_reply()

### Community 192 - "XCTestCase"
Cohesion: 0.09
Nodes (8): AudioSessionPolicyTests, ConversationControllerTests.Rig, AmbientForwardingTests, WakePhraseAloneTests, WakeStraightToListeningTests, What is verified and what is not, NovaGlasses, XCTest

### Community 196 - "InterruptedToolCallTests"
Cohesion: 0.26
Nodes (3): FakeToolUseBlock, InterruptedToolCallTests, _call()

### Community 197 - "post"
Cohesion: 0.08
Nodes (18): logout_all(), adopt_claude_thread(), _authorized(), coding_socket(), coding_status(), get_coding_session(), list_claude_threads(), list_coding_sessions() (+10 more)

### Community 198 - "Entry"
Cohesion: 0.36
Nodes (3): AudioLog, Entry, .body

### Community 201 - "meeting_service.py"
Cohesion: 0.07
Nodes (8): PromptEnums, BaseDao, MeetingChunkDao, MessageDao, ProjectDao, ResponsibilityDao, ReportType, EscapingTests

### Community 202 - "split_wake_phrase"
Cohesion: 0.17
Nodes (7): _canonical_wake_text(), has_stop_phrase(), has_wake_phrase(), normalize_wake_text(), split_wake_phrase(), SplitWakePhraseTests, WakePhraseTests

### Community 204 - "iter_in_thread"
Cohesion: 0.25
Nodes (4): chat_stream(), event_source(), sse_event(), iter_in_thread()

### Community 207 - "_FakeTable"
Cohesion: 0.13
Nodes (4): CheckForStaleConversationsLoopTests, _FakeResponse, _FakeSupabaseClient, _FakeTable

### Community 208 - "shell.py"
Cohesion: 0.22
Nodes (5): classify(), _clip(), _resolve_cwd(), run(), _scratch_pair()

### Community 209 - "FakeConversationService"
Cohesion: 0.22
Nodes (3): FakeConversationService, FakeMcpService, FakeToolDao

### Community 218 - "Phase"
Cohesion: 0.29
Nodes (7): Phase, idle, listening, off, sentryBlocked, speaking, thinking

### Community 223 - "main.py"
Cohesion: 0.15
Nodes (6): _allowed_origins(), health(), lifespan(), root(), _broadcast(), face_socket()

### Community 224 - "SocketConnectionState"
Cohesion: 0.40
Nodes (5): SocketConnectionState, connected, connecting, disconnected, unauthorized

## Ambiguous Edges - Review These
- `TTS conversion enhancer prompt (empty)` → `Voice mode tone guidelines`  [AMBIGUOUS]
  prompting/tts_conversion_enhancer_prompt.txt · relation: conceptually_related_to

## Knowledge Gaps
- **169 isolated node(s):** `UserNotifications`, `.serverURLString`, `.summary`, `AudioToolbox`, `.count` (+164 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1612 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **88 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `TTS conversion enhancer prompt (empty)` and `Voice mode tone guidelines`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `NovaGlasses` connect `WakeDetecting` to `XCTestCase`, `.look`, `ConversationController`?**
  _High betweenness centrality (0.321) - this node is a cross-community bridge._
- **Are the 43 inferred relationships involving `AgentLoop` (e.g. with `Server behaviour` and `PromptEnums`) actually correct?**
  _`AgentLoop` has 43 INFERRED edges - model-reasoned connections that need verification._
- **What connects `UserNotifications`, `.serverURLString`, `.summary` to the rest of the system?**
  _169 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Tool` be split into smaller, more focused modules?**
  _Cohesion score 0.12903225806451613 - nodes in this community are weakly interconnected._
- **Why does `Vision: "Hey Nova, what do you see?"` connect `.look` to `WakeDetecting`?**
  _High betweenness centrality (0.319) - this node is a cross-community bridge._
- **Are the 21 inferred relationships involving `Conversation` (e.g. with `_is_stale()` and `ConversationDao`) actually correct?**
  _`Conversation` has 21 INFERRED edges - model-reasoned connections that need verification._