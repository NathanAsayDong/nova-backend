# Graph Report - nova-backend  (2026-10-30)

## Corpus Check
- 231 files · ~198,925 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: (none) 3, .mdc 1, .pbxproj 1)

## Summary
- 4941 nodes · 11620 edges · 226 communities (127 shown, 99 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 1257 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9dc4430e`
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
- _most_recent_local_midnight_utc
- processes.py
- time
- test_memory_chunk_service.py
- MeetingError
- CursorService
- MeetingService
- FileOperationTests
- CodingSession
- Update
- ConversationController
- ElevenLabsService
- .scaled
- test_auth_service.py
- LiveReply
- auth_controller.py
- .start
- __main__.py
- VisionService
- FakeChunkDao
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
- TurnTimer
- AuthService
- auth_service.py
- ConversationDao
- TwilioErrorClassificationTests
- FakeMessage
- FakePersonaDao
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
- ConversationService
- nova_controller.py
- McpServer
- PersonaService
- TwilioService
- HttpGateTests
- ._conversation_turn
- faces_controller.py
- SessionManager
- parse_gate_reply
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
- test_coding_service.py
- build_memory_service
- test_responsibility_service.py
- ASRService
- AsrLock
- pending
- Mac code agent daemon
- FakeTaskDao
- ServiceMethodToolConfig
- fake_stream
- ._run_begin
- email_service.py
- NovaSocket
- Keys
- FaceService
- Sendable
- audio_file_bytes
- VoiceMode
- .repair_tool_pairing
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
- SidekickSocketTests
- PromptSourceTests
- EndSessionTests
- SidekickSession
- worker.py
- asr-bench.py
- Link
- agent_loop.py
- ._to_dict
- FakeDao
- ClassificationTests
- CaptureEngine
- history_compaction.py
- argparse
- SidekickConnection
- WorkingTreeTests
- AudioRouteManager
- .isOnlyWakePhrase
- run_migrations.py
- SpokenProse
- TTSService
- RelayTokenTests
- SpeechWakeDetector
- CodeService
- clamp_spoken
- PerformTests
- speech_summary
- .iter_sentence_chunks
- GoodbyeTimingTests
- .completed
- AgentLoop
- NovaGlasses
- StatusTextTests
- worktree.py
- PassSentinelTests
- Rig
- CLAUDE.md
- asyncio
- install.sh
- uninstall.sh
- ReportMediumTests
- nova-backend
- os
- CurrentModelTests
- FakeHttp
- BackgroundTests
- DemoService
- CameraError
- match
- VisionRoutesTests
- NovaGlasses
- prepare
- sidekick_controller.py
- AddPersonView
- PersonaPrompt
- .setUp
- protocol.py
- .look
- replay_request.py
- .wantsToSee
- LookToolExclusionTests
- FakeAgentLoop
- requests
- MacSessionLifecycleTests
- XCTestCase
- ClaudeCreditsService
- SentryModeTests
- .run_terminal_command
- InterruptedToolCallTests
- post
- Entry
- ThinkingPulseTests
- GuardrailTests
- get_conversation_messages
- split_wake_phrase
- test_settings_service.py
- FakeResponsibilityDao
- _said
- AgentLink
- _FakeTable
- test_process_supervisor.py
- EmbeddingService
- FinishedSessionTowerTests
- HostEnvironmentPromptTests
- FallbackTests
- FallbackTests
- TranscribeUtteranceTests
- GlassesCannotRecordMeetingsTests
- APIError
- VisionClient
- .decode
- .test_a_live_turn_reads_deltas_then_exposes_the_message
- test_persona_service.py
- face_controller.py
- FakeConversationService

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

## Communities (226 total, 99 thin omitted)

### Community 0 - "Tool"
Cohesion: 0.17
Nodes (4): ToolDao, Tool, FakeToolDao, ToolServiceTests

### Community 1 - "Conversation"
Cohesion: 0.06
Nodes (15): _handle_inbound(), _is_stale(), resolve_sms_conversation(), _run_sms_turn(), Conversation, ConversationClosedError, PrefetchedConversationTests, fake_stream() (+7 more)

### Community 2 - "SimpleFinancesService"
Cohesion: 0.11
Nodes (6): SimplApiError, SimplConfigurationError, SimpleFinancesService, response(), SimpleFinancesServiceTest, SimplFinancesToolRegistrationTest

### Community 3 - "text"
Cohesion: 0.13
Nodes (6): ToolUseStarted, AuthenticationTests, forward(), PathTokenRouteTests, SenderGateTests, text()

### Community 5 - "test_openai_loop.py"
Cohesion: 0.17
Nodes (7): FakeClient, FakeFunctionCall, FakeResponse, FakeResponsesAPI, FakeTool, FakeToolService, OpenAILoopTests

### Community 7 - "AgentLoopImageTests"
Cohesion: 0.33
Nodes (4): AgentLoopImageTests, FakeMessage, FakeTextBlock, FakeToolUseBlock

### Community 8 - ".run_agent"
Cohesion: 0.11
Nodes (3): BackgroundAgentTests, ReportTypeTests, ResponsibilityRunToolRestrictionTests

### Community 9 - "UpdateDeliveryService"
Cohesion: 0.13
Nodes (3): _env_int(), UpdateDeliveryService, QuietHoursTests

### Community 10 - "make_update"
Cohesion: 0.16
Nodes (10): at(), BadgeOnlyTests, build_service(), CallDeliveryTests, EmailDeliveryTests, make_update(), SettleCallTests, SmsDeliveryTests (+2 more)

### Community 11 - "ClaudeService"
Cohesion: 0.06
Nodes (10): Server behaviour, ModelSwitchRequest, set_model(), _env_flag(), ClaudeService, _env_flag(), _maybe_dump_request(), _maybe_print_prompt() (+2 more)

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
Nodes (6): MemoryChunkDao, MemoryChunk, MemoryMatch, MemoryChunkService, ParseChunksTests, RetrievableQueryTests

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
Cohesion: 0.15
Nodes (16): _all(), await_ready(), check(), _entry(), kill_tree(), _log_paths(), pid_alive(), port_open() (+8 more)

### Community 22 - "time"
Cohesion: 0.11
Nodes (18): _all(), await_ready(), check(), classify(), _entry(), kill_tree(), _log_paths(), pid_alive() (+10 more)

### Community 23 - "test_memory_chunk_service.py"
Cohesion: 0.07
Nodes (13): build_service(), FakeClaudeResponse, FakeClaudeService, FakeConversationService, FakeEmbeddingService, FakeMemoryChunkDao, FakeTextBlock, FetchMemoryTests (+5 more)

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
Nodes (6): UpdateDao, DeliveryStatus, ReportType, Update, UpdateService, EscapingTests

### Community 30 - "ConversationController"
Cohesion: 0.10
Nodes (9): Capture, ConversationController, .idleMessage, .isEnabled, .isWorking, .wakeWatching, Once, PhotoSlot (+1 more)

### Community 31 - "ElevenLabsService"
Cohesion: 0.11
Nodes (7): _describe_failure(), ElevenLabsService, OpenAITTS, _requested_provider(), ElevenLabsRequestTests, _env(), ProviderSelectionTests

### Community 33 - "test_auth_service.py"
Cohesion: 0.09
Nodes (4): NovaSessionDao, row_to_session(), NovaSession, RowConversionTests

### Community 35 - "auth_controller.py"
Cohesion: 0.09
Nodes (10): _client_ip(), current_session(), list_sessions(), login(), logout(), AuthNotConfigured, BadCredentials, LockedOut (+2 more)

### Community 37 - "__main__.py"
Cohesion: 0.13
Nodes (7): Config, _flag(), load_env_file(), _configure_logging(), main(), _run(), _task()

### Community 38 - "VisionService"
Cohesion: 0.13
Nodes (4): VisionService, ContentBlocksTests, LookToolTests, phone()

### Community 42 - "build_service"
Cohesion: 0.15
Nodes (6): build_service(), CreateTests, FakeProjectDao, FakeUpdateService, ListAndCancelTests, soon()

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
Cohesion: 0.05
Nodes (25): MeetingSegment, build_service(), ChunkingTests, CommitSegmentsTests, DeleteMeetingTests, FakeAgentLoop, FakeClaudeService, FakeConversationDao (+17 more)

### Community 48 - "pathlib"
Cohesion: 0.14
Nodes (8): main(), _hotwords(), _load_parakeet(), missing_cuda_libraries(), _nvidia_wheel_dll_dirs(), _platform_default_provider(), _resolve_whisper_device(), _setup_cuda_libraries()

### Community 49 - "call_controller.py"
Cohesion: 0.10
Nodes (15): answer_call(), call_status(), _escape(), mint_relay_token(), _opening_prompt(), relay_socket(), start_turn(), run_after_previous() (+7 more)

### Community 52 - "TurnTimer"
Cohesion: 0.10
Nodes (9): _emit(), mark(), TurnTimer, _drain(), _FakeMessage, _FakeStream, _FakeUsage, TurnStreamUsageMarkTests (+1 more)

### Community 53 - "AuthService"
Cohesion: 0.10
Nodes (8): AuthGate, bearer_token(), _header(), is_exempt(), AuthService, build_app(), ExemptionTests, SidekickAuthTests

### Community 54 - "auth_service.py"
Cohesion: 0.14
Nodes (3): _hash_token(), _now(), ConfigurationTests

### Community 55 - "ConversationDao"
Cohesion: 0.08
Nodes (9): ConversationDao, ProjectDao, Project, ProjectService, CodeServiceTestCase, FakeConversationDao, FakeProjectDao, ProjectResolutionTests (+1 more)

### Community 56 - "TwilioErrorClassificationTests"
Cohesion: 0.15
Nodes (6): describe_twilio_error(), is_permanent_twilio_error(), SimpleNamespace_Exception, TwilioErrorClassificationTests, reject(), flake()

### Community 57 - "FakeMessage"
Cohesion: 0.24
Nodes (6): FakeMessage, FakeTextBlock, fake_stream(), fake_stream(), fake_stream(), ToolTurnSpeechTests

### Community 58 - "FakePersonaDao"
Cohesion: 0.14
Nodes (7): build_service(), CachingTests, FakePersonaDao, LoadingTests, seed_row(), ToolFacingWrapperTests, VersioningAndRollbackTests

### Community 59 - "ConversationLoopStreamTests"
Cohesion: 0.15
Nodes (4): ConversationLoopStreamTests, fake_stream(), fake_stream(), EventStreamTests

### Community 61 - "SpeechPlayer"
Cohesion: 0.07
Nodes (7): MP3StreamDecoder, PlaybackWatchdog, SpeechPlayer, .isBusy, .now, Stream, PlaybackWatchdogTests

### Community 62 - "EndpointDecisionTests"
Cohesion: 0.09
Nodes (6): run_speculative_transcription(), endpoint_decision(), _endpoint_scale(), EndpointDecision, silence_budget_ms(), EndpointDecisionTests

### Community 63 - "ImageStore"
Cohesion: 0.15
Nodes (4): ImageStore, VisionImage, GlassesSocketTests, ImageStoreTests

### Community 64 - "FakeCamera"
Cohesion: 0.22
Nodes (4): FakeCamera, FakeVision, settle(), VisionControllerTests

### Community 65 - "ConversationControllerTests"
Cohesion: 0.06
Nodes (12): PCMFormat, PreRollBuffer, .count, AudioFramingTests, ConversationControllerTests, ConversationControllerTests.Rig, FakePlayer, .isBusy (+4 more)

### Community 67 - "test_spoken_reply.py"
Cohesion: 0.16
Nodes (6): _comparable(), is_repeat(), _plain_text(), strip_speak_tags(), IsRepeatTests, StripSpeakTagsTests

### Community 68 - "ClientEvent"
Cohesion: 0.06
Nodes (26): AudioRole, final, progress, status, wake, CapturePurpose, sentry, turn (+18 more)

### Community 70 - "ConversationService"
Cohesion: 0.10
Nodes (3): MessageDao, Message, ConversationService

### Community 71 - "nova_controller.py"
Cohesion: 0.08
Nodes (21): _canonical_wake_text(), chat_stream(), event_source(), get_nova_power(), get_nova_state(), has_stop_phrase(), normalize_wake_text(), parse_conversation_id() (+13 more)

### Community 72 - "McpServer"
Cohesion: 0.20
Nodes (3): McpServer, _now(), _parse_expiry()

### Community 74 - "TwilioService"
Cohesion: 0.09
Nodes (5): main(), report(), TwilioConfigurationError, TwilioService, ConfigurationGuardTests

### Community 76 - "._conversation_turn"
Cohesion: 0.03
Nodes (7): persist(), _memory_block_budget_seconds(), _PassHold, strip_expects_reply(), _strip_expects_reply_events(), GlassesPromptSourceTests, SanitizeMcpHistoryTests

### Community 77 - "faces_controller.py"
Cohesion: 0.09
Nodes (14): add_sample(), create_person(), delete_person(), _enroll(), list_people(), capture_failed(), read_jpeg_body(), upload_image() (+6 more)

### Community 78 - "SessionManager"
Cohesion: 0.20
Nodes (4): _as_int(), _flatten(), _ms_to_iso(), SessionManager

### Community 79 - "parse_gate_reply"
Cohesion: 0.18
Nodes (3): parse_gate_reply(), SidekickGate, GateReplyTests

### Community 80 - ".add"
Cohesion: 0.10
Nodes (11): Cancellable, ConversationIdStore, EarconPlaying, GlassesCamera, MainScheduler, NovaSocketing, Scheduling, SpeechPlaying (+3 more)

### Community 83 - "FakeMcpServerDao"
Cohesion: 0.17
Nodes (3): build_service(), FakeMcpServerDao, McpServerServiceTests

### Community 87 - "Person"
Cohesion: 0.11
Nodes (3): PersonDao, Person, FakePersonDao

### Community 88 - "test_sms.py"
Cohesion: 0.07
Nodes (12): BipConfigurationError, BipRequestError, BipService, _describe_response_error(), is_permanent_bip_error(), normalize_phone_number(), _parse_number_list(), SmsRecipientError (+4 more)

### Community 89 - "ServerEvent"
Cohesion: 0.06
Nodes (27): message, ServerEvent, audioStreamChunk, audioStreamEnd, audioStreamStart, captureRequest, chunkReceived, done (+19 more)

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

### Community 100 - "fake_stream"
Cohesion: 0.11
Nodes (6): fake_stream(), fake_stream(), fake_stream(), fake_stream(), FailureSpeechTests, _FakeBadRequestError

### Community 101 - "._run_begin"
Cohesion: 0.23
Nodes (6): BeginFlowTests, fake_get(), fake_post(), fake_post(), fake_post(), FakeResponse

### Community 104 - "Keys"
Cohesion: 0.08
Nodes (23): Keys, assistantText, bytes, chunkBase64, client, code, conversationId, count (+15 more)

### Community 105 - "FaceService"
Cohesion: 0.11
Nodes (5): FaceService, _normalise(), face_row(), FaceServiceTests, FacesRoutesTests

### Community 106 - "Sendable"
Cohesion: 0.06
Nodes (25): Note, Phase, idle, listening, off, sentryBlocked, speaking, thinking (+17 more)

### Community 107 - "audio_file_bytes"
Cohesion: 0.17
Nodes (7): audio_file_bytes(), is_raw_pcm(), _pcm_params(), suffix_for_mime(), transcribe_serialized(), emit_partial_transcript(), AudioFileBytesTests

### Community 108 - "VoiceMode"
Cohesion: 0.26
Nodes (4): VoiceMode, conversation, sentry, VoiceModeStore

### Community 110 - "test_asr_filters.py"
Cohesion: 0.26
Nodes (4): drop_hallucination(), DropHallucinationTests, _segment(), WhisperSegmentFilterTests

### Community 111 - "FakeDao"
Cohesion: 0.18
Nodes (4): CompleteAndRefreshTests, ConnectorFilteringTests, FakeDao, oauth_server()

### Community 113 - "sessions.py"
Cohesion: 0.19
Nodes (3): _contained(), make_guard(), _is_prose()

### Community 114 - "AppModel"
Cohesion: 0.05
Nodes (22): AppModel, .serverURLString, NovaGlassesApp, .body, RootView, .body, AuthStore, .baseQuery (+14 more)

### Community 115 - "meeting_service.py"
Cohesion: 0.07
Nodes (7): BaseDao, MeetingChunkDao, MeetingNotesDao, ResponsibilityDao, MeetingChunk, MeetingNotes, MeetingStatus

### Community 117 - "host_environment_prompt.py"
Cohesion: 0.32
Nodes (3): host_environment_prompt(), _host_kind(), _machine_line()

### Community 119 - "Foundation"
Cohesion: 0.10
Nodes (10): AudioToolbox, AVFoundation, Foundation, AudioSessionPolicy, MWDATCamera, MWDATCore, Observation, Security (+2 more)

### Community 120 - "Earcon"
Cohesion: 0.13
Nodes (14): Earcons, Earcon, cancel, done, error, shutter, sidekickCue, sidekickOff (+6 more)

### Community 125 - "worker.py"
Cohesion: 0.16
Nodes (10): BuildJobsTests, build_jobs(), _recover_stuck_tasks(), _run_check_for_responsibilities(), _run_check_for_stale_conversations(), _run_deliver_pending_updates(), _run_process_conversations(), _run_scheduled_tasks() (+2 more)

### Community 126 - "asr-bench.py"
Cohesion: 0.36
Nodes (4): cut_clips(), default_audio(), load(), main()

### Community 128 - "agent_loop.py"
Cohesion: 0.07
Nodes (9): PromptSourceEnum, is_sidekick_pass(), MessageRole, TurnStream, ToolExecutionError, FakeProjectDao, FakeMessage, FakeTextBlock (+1 more)

### Community 130 - "FakeDao"
Cohesion: 0.08
Nodes (5): GateTestCase, WebSocketGateTests, AuthenticateTests, AuthServiceTestCase, FakeDao

### Community 135 - "history_compaction.py"
Cohesion: 0.20
Nodes (15): _block_chars(), cap_messages(), clear_old_tool_results(), _clearable_blocks(), compact_history(), _env_int(), _is_plain_user_turn(), _history() (+7 more)

### Community 136 - "argparse"
Cohesion: 0.36
Nodes (3): main(), main(), main()

### Community 137 - "SidekickConnection"
Cohesion: 0.17
Nodes (3): Utterances, sidekick_socket(), SidekickConnection

### Community 139 - "AudioRouteManager"
Cohesion: 0.22
Nodes (3): AudioRouteManager, Route, .summary

### Community 141 - "run_migrations.py"
Cohesion: 0.16
Nodes (4): main(), migration_files(), _jsonable(), SQLService

### Community 148 - "clamp_spoken"
Cohesion: 0.23
Nodes (5): deliver(), mark_first_speech(), _clamp(), clamp_spoken(), ClampSpokenTests

### Community 153 - ".completed"
Cohesion: 0.13
Nodes (7): fake_stream(), fake_stream(), fake_stream(), fake_stream(), TurnStreamTests, get_final_message(), fake_stream()

### Community 154 - "AgentLoop"
Cohesion: 0.05
Nodes (22): AgentLoop, ToolService, fake_get_response(), FakeConversationService, FakeMessage, FakeTextBlock, FakeToolDao, FakeUpdateService (+14 more)

### Community 155 - "NovaGlasses"
Cohesion: 0.29
Nodes (6): Build and test (CLI), Code map, How it behaves, Install on your iPhone, NovaGlasses, On-device field checklist

### Community 157 - "worktree.py"
Cohesion: 0.23
Nodes (7): create(), _git(), remove(), resolve_repo(), slugify(), Workspace, WorktreeError

### Community 158 - "PassSentinelTests"
Cohesion: 0.17
Nodes (7): FakeMessage, FakeTextBlock, FakeToolUseBlock, _live(), get_final_message(), fake_stream(), PassSentinelTests

### Community 161 - "asyncio"
Cohesion: 0.07
Nodes (18): can_use_tool(), health(), lifespan(), root(), _callback_page(), create_mcp_server(), delete_mcp_server(), list_mcp_servers() (+10 more)

### Community 170 - "os"
Cohesion: 0.13
Nodes (9): classify(), _clip(), _resolve_cwd(), run(), _scratch_pair(), _allowed_origins(), _build_file_logger(), _default_log_path() (+1 more)

### Community 172 - "FakeHttp"
Cohesion: 0.12
Nodes (8): basic(), build_service(), FakeHttp, FakeResponse, InboundSecretTests, InfobipRequestTests, RecipientAllowlistTests, SendSmsTests

### Community 175 - "CameraError"
Cohesion: 0.15
Nodes (7): CameraError, .errorDescription, failed, glassesAudioNotUp, noCamera, notReady, timeout

### Community 176 - "match"
Cohesion: 0.35
Nodes (4): GalleryPerson, match(), MatchTests, unit()

### Community 177 - "VisionRoutesTests"
Cohesion: 0.26
Nodes (3): Identification, FakeFaceService, VisionRoutesTests

### Community 179 - "prepare"
Cohesion: 0.31
Nodes (3): prepare(), jpeg(), PrepareTests

### Community 180 - "sidekick_controller.py"
Cohesion: 0.12
Nodes (6): _remove(), transcribe_utterance(), has_be_quiet_phrase(), _normalize(), SidekickService, BeQuietPhraseTests

### Community 181 - "AddPersonView"
Cohesion: 0.24
Nodes (6): .api, AddPersonView, .body, FacesView, .body, PhotosUI

### Community 183 - ".setUp"
Cohesion: 0.12
Nodes (4): DirectTurnCounterTests, fake_transcribe(), FakeGate, FakeSidekickLoop

### Community 184 - "protocol.py"
Cohesion: 0.39
Nodes (3): _artifact_for(), encode(), _truncate()

### Community 185 - ".look"
Cohesion: 0.10
Nodes (12): Vision: "Hey Nova, what do you see?", Client → server, Connecting, Deviations from the brief and additions, Interjections, Prompt and tools, Server → client, Sidekick protocol: `WS /ws/sidekick` (+4 more)

### Community 186 - "replay_request.py"
Cohesion: 0.20
Nodes (5): main(), one_call(), main(), one_call(), variants()

### Community 190 - "requests"
Cohesion: 0.27
Nodes (7): backend_url(), close_current_conversation(), fetch_conversation_info(), fetch_health(), fetch_projects(), fetch_tools(), stream_reply()

### Community 192 - "XCTestCase"
Cohesion: 0.12
Nodes (5): AudioSessionPolicyTests, AmbientForwardingTests, WakePhraseAloneTests, WakeStraightToListeningTests, What is verified and what is not

### Community 193 - "ClaudeCreditsService"
Cohesion: 0.14
Nodes (4): get_all_settings(), get_available_models(), get_claude_credits(), ClaudeCreditsService

### Community 196 - "InterruptedToolCallTests"
Cohesion: 0.26
Nodes (3): FakeToolUseBlock, InterruptedToolCallTests, _call()

### Community 197 - "post"
Cohesion: 0.08
Nodes (20): logout_all(), adopt_claude_thread(), _authorized(), coding_socket(), coding_status(), get_coding_session(), list_claude_threads(), list_coding_sessions() (+12 more)

### Community 198 - "Entry"
Cohesion: 0.36
Nodes (3): AudioLog, Entry, .body

### Community 201 - "get_conversation_messages"
Cohesion: 0.24
Nodes (5): close_conversation(), get_conversation(), get_conversation_messages(), _parse_uuid(), _project_payload()

### Community 202 - "split_wake_phrase"
Cohesion: 0.23
Nodes (4): has_wake_phrase(), split_wake_phrase(), SplitWakePhraseTests, WakePhraseTests

### Community 207 - "_FakeTable"
Cohesion: 0.17
Nodes (3): _FakeResponse, _FakeSupabaseClient, _FakeTable

### Community 208 - "test_process_supervisor.py"
Cohesion: 0.13
Nodes (4): fetch(), main(), sha256(), MirrorTests

### Community 217 - "GlassesCannotRecordMeetingsTests"
Cohesion: 0.32
Nodes (3): GlassesCannotRecordMeetingsTests, fake_stream(), get_all()

### Community 218 - "APIError"
Cohesion: 0.29
Nodes (5): APIError, badResponse, .errorDescription, server, unauthorized

## Ambiguous Edges - Review These
- `TTS conversion enhancer prompt (empty)` → `Voice mode tone guidelines`  [AMBIGUOUS]
  prompting/tts_conversion_enhancer_prompt.txt · relation: conceptually_related_to

## Knowledge Gaps
- **165 isolated node(s):** `UserNotifications`, `.serverURLString`, `.summary`, `AudioToolbox`, `.count` (+160 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1570 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **99 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `TTS conversion enhancer prompt (empty)` and `Voice mode tone guidelines`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `NovaGlasses` connect `NovaGlasses` to `XCTestCase`, `.look`, `ConversationController`?**
  _High betweenness centrality (0.315) - this node is a cross-community bridge._
- **Are the 43 inferred relationships involving `AgentLoop` (e.g. with `Server behaviour` and `PromptEnums`) actually correct?**
  _`AgentLoop` has 43 INFERRED edges - model-reasoned connections that need verification._
- **What connects `UserNotifications`, `.serverURLString`, `.summary` to the rest of the system?**
  _165 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Conversation` be split into smaller, more focused modules?**
  _Cohesion score 0.05837173579109063 - nodes in this community are weakly interconnected._
- **Why does `Vision: "Hey Nova, what do you see?"` connect `.look` to `NovaGlasses`?**
  _High betweenness centrality (0.315) - this node is a cross-community bridge._
- **Are the 21 inferred relationships involving `Conversation` (e.g. with `_is_stale()` and `ConversationDao`) actually correct?**
  _`Conversation` has 21 INFERRED edges - model-reasoned connections that need verification._