# Graph Report - nova-backend  (2026-11-10)

## Corpus Check
- 234 files · ~205,172 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: (none) 3, .mdc 1, .pbxproj 1)

## Summary
- 5073 nodes · 11899 edges · 235 communities (135 shown, 100 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 1270 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `009278a1`
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
- time
- build_service
- MeetingError
- IsIdleTests
- MeetingService
- FileOperationTests
- CodingSession
- Update
- .handle
- ElevenLabsService
- _install_fake_modules
- NovaSession
- LiveReply
- test_auth_service.py
- SessionManager
- __main__.py
- VisionService
- FakeChunkDao
- DATGlassesCamera
- _FakeStream
- build_service
- ResponsibilityService
- Responsibility
- McpOAuthService
- make_update
- build_service
- asr_service.py
- call_controller.py
- McpServerService
- BackgroundTests
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
- vision_service.py
- FakeCamera
- ConversationControllerTests
- ._artifact_for_tool
- speech_summary
- ClientEvent
- MacShellTests
- Conversation
- nova_controller.py
- McpServer
- PersonaService
- TwilioService
- HttpGateTests
- AgentLoop
- test_vision.py
- PreRollBuffer
- sidekick_controller.py
- SidekickController
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
- AgentBindingTests
- build_memory_service
- test_responsibility_service.py
- ASRService
- AsrLock
- pathlib
- Mac code agent daemon
- FakeTaskDao
- ServiceMethodToolConfig
- FailureSpeechTests
- ._run_begin
- UpdateDeliveryService
- NovaSocket
- Keys
- FaceService
- MemoryChunk
- test_glasses_voice.py
- VoiceMode
- .repair_tool_pairing
- test_asr_filters.py
- FakeDao
- MemoryInjectionTests
- permissions.py
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
- ConversationController
- Qwen3-TTS: Nova's local TTS fallback
- agent_loop.py
- ._to_dict
- FakeDao
- ClassificationTests
- sessions.py
- CaptureEngine
- history_compaction.py
- ToolExecutionError
- SidekickConnection
- WorkingTreeTests
- AudioRouteManager
- .isOnlyWakePhrase
- run_migrations.py
- SpokenProse
- TTSService
- .setUp
- RelayTokenTests
- SpeechWakeDetector
- AuthenticateTests
- ._conversation_turn
- PerformTests
- SpokenTrackTests
- .iter_sentence_chunks
- GoodbyeTimingTests
- ToolService
- .conversation_loop_events
- NovaGlasses
- test_process_supervisor.py
- FallbackChainTests
- PassSentinelTests
- Rig
- CLAUDE.md
- asyncio
- install.sh
- uninstall.sh
- settings_controller.py
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
- Hosting Nova off the home network
- os
- AddPersonView
- PersonaPrompt
- .setUp
- conversation_controller.py
- .look
- replay_request.py
- .wantsToSee
- endpointing_service.py
- FakeAgentLoop
- dict
- MacSessionLifecycleTests
- XCTestCase
- EventCodingTests
- SentryModeTests
- CreateScheduleRequirementTests
- InterruptedToolCallTests
- ._spoken_track
- test_persona_service.py
- ThinkingPulseTests
- GuardrailTests
- BaseDao
- StatusTextTests
- test_settings_service.py
- Link
- FakeSocket
- AgentLink
- _FakeTable
- shell.py
- ConversationTurnMcpDisabledReplayTests
- FinishedSessionTowerTests
- protocol.py
- FallbackTests
- .split_sms_body
- ReportMediumTests
- FakeResponsibilityDao
- Phase
- .allowed_sms_senders
- _PassHold
- transcribe_utterance
- CheckForStaleConversationsLoopTests
- ConnectorFilteringTests
- FakeClaudeService
- FakeAgentLoop
- ReplyQueue
- FakeNotesDao
- FakeResponse
- _describe_failure
- FakeConversationDao
- FakeEmbeddingService
- FakeUpdateService

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
- `Install (Windows tower)` --references--> `_load_model()`  [INFERRED]
  docs/QWEN_TTS.md → src/service/qwen_tts_service.py
- `Server behaviour` --references--> `audio_file_bytes()`  [INFERRED]
  SIDEKICK_PROTOCOL.md → src/controller/audio_ws.py
- `Server → client` --references--> `stream_tts_audio()`  [INFERRED]
  SIDEKICK_PROTOCOL.md → src/controller/nova_controller.py
- `Server behaviour` --references--> `AgentLoop`  [INFERRED]
  SIDEKICK_PROTOCOL.md → src/harness/agent_loop.py
- `Server behaviour` --references--> `ClaudeService`  [INFERRED]
  SIDEKICK_PROTOCOL.md → src/service/claude_service.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Remote access path: Firebase frontend to Cloudflare Tunnel to tower API** — docs_hosting_firebase_hosting, docs_hosting_cloudflare_tunnel, docs_hosting_tower_api [EXTRACTED 0.95]
- **Mac agent core design principles** — mac_agent_readme_dial_out, mac_agent_readme_sessions_as_threads, mac_agent_readme_git_worktree [EXTRACTED 1.00]
- **Persisted-action safety rules across foreground and background agents** — prompting_nova_persona_prompt_confirm_persisted_actions, prompting_nova_persona_prompt_clarify_before_executing, prompting_background_agent_prompt_no_outward_actions [INFERRED 0.85]

## Communities (235 total, 100 thin omitted)

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
Cohesion: 0.13
Nodes (7): AuthenticationTests, forward(), make_request(), PathTokenRouteTests, SenderGateTests, go(), text()

### Community 5 - "test_openai_loop.py"
Cohesion: 0.18
Nodes (7): FakeClient, FakeFunctionCall, FakeResponse, FakeResponsesAPI, FakeTool, FakeToolService, OpenAILoopTests

### Community 6 - "Rig"
Cohesion: 0.13
Nodes (6): FakePlayer, .isBusy, FakeWake, Item, ManualScheduler, Rig

### Community 7 - "AgentLoopImageTests"
Cohesion: 0.16
Nodes (6): AgentLoopImageTests, fake_stream(), FakeConversationService, FakeMessage, FakeTextBlock, FakeToolUseBlock

### Community 8 - ".run_agent"
Cohesion: 0.11
Nodes (3): BackgroundAgentTests, ReportTypeTests, ResponsibilityRunToolRestrictionTests

### Community 9 - "._env"
Cohesion: 0.14
Nodes (4): CartesiaService, _cartesia(), CartesiaRequestTests, ProviderSelectionTests

### Community 10 - "make_update"
Cohesion: 0.14
Nodes (11): at(), BadgeOnlyTests, build_service(), CallDeliveryTests, EmailDeliveryTests, make_update(), QuietHoursTests, SettleCallTests (+3 more)

### Community 11 - "ClaudeService"
Cohesion: 0.09
Nodes (5): _env_flag(), ClaudeService, _maybe_print_prompt(), GenerationKwargsTests, ClaudeServiceMcpKwargsTests

### Community 12 - "GithubService"
Cohesion: 0.15
Nodes (4): GithubService, GithubServiceError, _FakeResponse, GithubServiceTests

### Community 13 - "build_service"
Cohesion: 0.08
Nodes (8): build_service(), CreateUpdateTests, FakeConversationDao, FakeProjectDao, FakeUpdateDao, make_update(), ReportTypeTests, ViewingTests

### Community 14 - "Nova system prompt (persona)"
Cohesion: 0.11
Nodes (15): Background agent prompt, Meeting follow-up prompt, Notify decision (email vs call), Meeting notes prompt, Meeting notes JSON output (title, summary, decisions, action items), Nova system prompt (persona), About Nate (user profile), agent_loop.py core tool-calling loop (+7 more)

### Community 15 - "MemoryChunkService"
Cohesion: 0.08
Nodes (4): EmbeddingService, MemoryChunkService, ParseChunksTests, RetrievableQueryTests

### Community 17 - "Harness"
Cohesion: 0.08
Nodes (19): LevelSmoother, Snapshot, State, calibrating, cooldown, idle, onset, speaking (+11 more)

### Community 19 - "ScheduledTaskService"
Cohesion: 0.08
Nodes (5): ScheduledTaskDao, ScheduledTask, TaskStatus, ScheduledTaskService, CurrentTimeTests

### Community 20 - "_most_recent_local_midnight_utc"
Cohesion: 0.10
Nodes (6): _most_recent_local_midnight_utc(), IsPastRolloverTests, build_service(), CheckForStaleConversationsTests, FakeConversationDao, MostRecentLocalMidnightUtcTests

### Community 21 - "json"
Cohesion: 0.15
Nodes (16): _all(), await_ready(), check(), _entry(), kill_tree(), _log_paths(), pid_alive(), port_open() (+8 more)

### Community 22 - "time"
Cohesion: 0.11
Nodes (18): _all(), await_ready(), check(), classify(), _entry(), kill_tree(), _log_paths(), pid_alive() (+10 more)

### Community 23 - "build_service"
Cohesion: 0.06
Nodes (13): build_service(), FakeClaudeResponse, FakeClaudeService, FakeConversationService, FakeEmbeddingService, FakeMemoryChunkDao, FakeTextBlock, FetchMemoryTests (+5 more)

### Community 24 - "MeetingError"
Cohesion: 0.09
Nodes (19): transcribe_segments_serialized(), delete_meeting(), get_active_meeting(), get_meeting(), get_meeting_segments(), list_meetings(), _meeting_error(), meeting_socket() (+11 more)

### Community 26 - "MeetingService"
Cohesion: 0.05
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

### Community 30 - ".handle"
Cohesion: 0.12
Nodes (3): Cancellable, Handle, Sentry mode

### Community 31 - "ElevenLabsService"
Cohesion: 0.25
Nodes (3): ElevenLabsService, _eleven_labs(), ElevenLabsRequestTests

### Community 32 - "_install_fake_modules"
Cohesion: 0.08
Nodes (7): _FakeTorch, _full_chain_env(), _install_fake_modules(), QwenTTSCooldownTests, QwenTTSGenerationTests, QwenTTSProviderSelectionTests, _raise_for_torch()

### Community 33 - "NovaSession"
Cohesion: 0.09
Nodes (4): NovaSessionDao, row_to_session(), NovaSession, RowConversionTests

### Community 35 - "test_auth_service.py"
Cohesion: 0.12
Nodes (6): AuthNotConfigured, BadCredentials, LockedOut, _now(), LockoutTests, LoginTests

### Community 37 - "__main__.py"
Cohesion: 0.13
Nodes (7): Config, _flag(), load_env_file(), _configure_logging(), main(), _run(), _task()

### Community 38 - "VisionService"
Cohesion: 0.12
Nodes (4): VisionService, ContentBlocksTests, LookToolTests, phone()

### Community 40 - "DATGlassesCamera"
Cohesion: 0.06
Nodes (18): AudioLog, Entry, CameraError, .errorDescription, failed, glassesAudioNotUp, noCamera, notReady (+10 more)

### Community 41 - "_FakeStream"
Cohesion: 0.18
Nodes (5): _drain(), _FakeMessage, _FakeStream, _FakeUsage, TurnStreamUsageMarkTests

### Community 42 - "build_service"
Cohesion: 0.10
Nodes (10): build_service(), CreateTests, FakeProjectDao, FakeUpdateService, ListAndCancelTests, pending(), RecoverStuckTests, RunDueTests (+2 more)

### Community 44 - "Responsibility"
Cohesion: 0.19
Nodes (4): Responsibility, at(), CheckForResponsibilitiesTests, DueTests

### Community 45 - "McpOAuthService"
Cohesion: 0.24
Nodes (3): McpOAuthService, _origin(), _path()

### Community 46 - "make_update"
Cohesion: 0.16
Nodes (5): ConversationResolutionTests, make_update(), OpeningPromptTests, TwiMLTests, form()

### Community 47 - "build_service"
Cohesion: 0.07
Nodes (18): MeetingSegment, build_service(), ChunkingTests, CommitSegmentsTests, DeleteMeetingTests, FakeProjectDao, FinalizeTests, FollowUpTests (+10 more)

### Community 48 - "asr_service.py"
Cohesion: 0.20
Nodes (8): main(), _hotwords(), _load_parakeet(), missing_cuda_libraries(), _nvidia_wheel_dll_dirs(), _platform_default_provider(), _resolve_whisper_device(), _setup_cuda_libraries()

### Community 49 - "call_controller.py"
Cohesion: 0.10
Nodes (15): answer_call(), call_status(), _escape(), mint_relay_token(), _opening_prompt(), relay_socket(), start_turn(), run_after_previous() (+7 more)

### Community 52 - "TurnTimer"
Cohesion: 0.18
Nodes (4): _emit(), mark(), TurnTimer, TurnTimerTests

### Community 53 - "test_auth_gate.py"
Cohesion: 0.11
Nodes (7): AuthGate, bearer_token(), _header(), is_exempt(), build_app(), ExemptionTests, SidekickAuthTests

### Community 54 - "AuthService"
Cohesion: 0.14
Nodes (3): AuthService, _hash_token(), ConfigurationTests

### Community 55 - "Project"
Cohesion: 0.06
Nodes (8): ProjectDao, Project, CodeService, ProjectService, CodeServiceTestCase, FakeConversationDao, FakeProjectDao, ProjectResolutionTests

### Community 56 - "TwilioErrorClassificationTests"
Cohesion: 0.15
Nodes (6): describe_twilio_error(), is_permanent_twilio_error(), SimpleNamespace_Exception, TwilioErrorClassificationTests, reject(), flake()

### Community 57 - "FakeMessage"
Cohesion: 0.22
Nodes (7): FakeMessage, FakeTextBlock, fake_stream(), fake_stream(), fake_stream(), ToolTurnSpeechTests, fake_stream()

### Community 58 - "FakePersonaDao"
Cohesion: 0.14
Nodes (7): build_service(), CachingTests, FakePersonaDao, LoadingTests, seed_row(), ToolFacingWrapperTests, VersioningAndRollbackTests

### Community 59 - "ConversationLoopStreamTests"
Cohesion: 0.13
Nodes (4): ConversationLoopStreamTests, fake_stream(), fake_stream(), EventStreamTests

### Community 61 - "SpeechPlayer"
Cohesion: 0.07
Nodes (7): MP3StreamDecoder, PlaybackWatchdog, SpeechPlayer, .isBusy, .now, Stream, PlaybackWatchdogTests

### Community 63 - "vision_service.py"
Cohesion: 0.08
Nodes (8): capture_failed(), CaptureFailed, ImageStore, _in_view_text(), is_image_block(), VisionImage, GlassesSocketTests, ImageStoreTests

### Community 64 - "FakeCamera"
Cohesion: 0.21
Nodes (4): FakeCamera, FakeVision, settle(), VisionControllerTests

### Community 67 - "speech_summary"
Cohesion: 0.08
Nodes (11): _clamp(), clamp_spoken(), _comparable(), is_repeat(), _plain_text(), speech_summary(), strip_speak_tags(), ClampSpokenTests (+3 more)

### Community 68 - "ClientEvent"
Cohesion: 0.09
Nodes (24): Note, AudioRole, final, progress, status, wake, CapturePurpose, sentry (+16 more)

### Community 70 - "Conversation"
Cohesion: 0.09
Nodes (5): ConversationDao, Conversation, ConversationService, FakeConversationService, ThreadResolutionTests

### Community 71 - "nova_controller.py"
Cohesion: 0.06
Nodes (26): _canonical_wake_text(), chat_stream(), event_source(), get_nova_power(), get_nova_state(), has_stop_phrase(), has_wake_phrase(), normalize_wake_text() (+18 more)

### Community 72 - "McpServer"
Cohesion: 0.19
Nodes (4): McpServer, _b64url(), _now(), _parse_expiry()

### Community 74 - "TwilioService"
Cohesion: 0.05
Nodes (16): backend_url(), close_current_conversation(), fetch_conversation_info(), fetch_health(), fetch_projects(), fetch_tools(), stream_reply(), main() (+8 more)

### Community 75 - "HttpGateTests"
Cohesion: 0.15
Nodes (3): GateTestCase, HttpGateTests, WebSocketGateTests

### Community 77 - "test_vision.py"
Cohesion: 0.09
Nodes (15): add_sample(), delete_person(), _enroll(), list_people(), read_jpeg_body(), upload_image(), DuplicatePerson, EnrollmentError (+7 more)

### Community 78 - "PreRollBuffer"
Cohesion: 0.19
Nodes (4): PCMFormat, PreRollBuffer, .count, AudioFramingTests

### Community 79 - "sidekick_controller.py"
Cohesion: 0.09
Nodes (6): has_be_quiet_phrase(), _normalize(), parse_gate_reply(), SidekickGate, BeQuietPhraseTests, GateReplyTests

### Community 80 - "SidekickController"
Cohesion: 0.14
Nodes (6): SocketConnectionState, connected, connecting, disconnected, unauthorized, SidekickController

### Community 81 - "fake_stream"
Cohesion: 0.15
Nodes (6): fake_stream(), FailureHistoryAndRetryTests, fake_stream(), fake_stream(), fake_stream(), _FakeBadRequestError

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
Cohesion: 0.18
Nodes (6): build_memory_service(), FakeConversationService, FakeEmbeddingService, FakeMemoryChunkDao, match(), RetrieveContextTests

### Community 93 - "test_responsibility_service.py"
Cohesion: 0.19
Nodes (4): build_service(), FakeProjectDao, FakeUpdateService, WindowTests

### Community 96 - "pathlib"
Cohesion: 0.18
Nodes (4): cut_clips(), default_audio(), load(), main()

### Community 97 - "Mac code agent daemon"
Cohesion: 0.16
Nodes (14): Nova code agent (Mac) README, Anthropic API key stripping, Mac dials out design, Per-session git worktree, Known limits (awake Mac, bounded replay, cache cost), launchd install and menu app, Mac code agent daemon, NOVA_CODE_TOKEN shared secret (+6 more)

### Community 101 - "._run_begin"
Cohesion: 0.29
Nodes (4): BeginFlowTests, fake_get(), fake_post(), FakeResponse

### Community 102 - "UpdateDeliveryService"
Cohesion: 0.09
Nodes (4): user_phone_number(), EmailService, _env_int(), UpdateDeliveryService

### Community 104 - "Keys"
Cohesion: 0.08
Nodes (24): Keys, assistantText, bytes, chunkBase64, client, code, conversationId, count (+16 more)

### Community 105 - "FaceService"
Cohesion: 0.12
Nodes (5): FaceService, _normalise(), face_row(), FaceServiceTests, FacesRoutesTests

### Community 106 - "MemoryChunk"
Cohesion: 0.18
Nodes (3): MemoryChunkDao, MemoryChunk, MemoryMatch

### Community 107 - "test_glasses_voice.py"
Cohesion: 0.09
Nodes (9): audio_file_bytes(), is_raw_pcm(), _pcm_params(), suffix_for_mime(), transcribe_serialized(), emit_partial_transcript(), run_speculative_transcription(), AudioFileBytesTests (+1 more)

### Community 108 - "VoiceMode"
Cohesion: 0.26
Nodes (4): VoiceMode, conversation, sentry, VoiceModeStore

### Community 110 - "test_asr_filters.py"
Cohesion: 0.26
Nodes (4): drop_hallucination(), DropHallucinationTests, _segment(), WhisperSegmentFilterTests

### Community 111 - "FakeDao"
Cohesion: 0.19
Nodes (5): fake_post(), CompleteAndRefreshTests, fake_post(), FakeDao, oauth_server()

### Community 113 - "permissions.py"
Cohesion: 0.22
Nodes (5): _contained(), make_guard(), can_use_tool(), health(), root()

### Community 114 - "AppModel"
Cohesion: 0.05
Nodes (23): AppModel, .baseURL, .serverURLString, NovaGlassesApp, .body, RootView, .body, AuthStore (+15 more)

### Community 115 - "meeting_service.py"
Cohesion: 0.11
Nodes (5): MeetingChunkDao, MeetingNotesDao, MeetingChunk, MeetingNotes, MeetingStatus

### Community 117 - "host_environment_prompt.py"
Cohesion: 0.31
Nodes (3): host_environment_prompt(), _host_kind(), _machine_line()

### Community 118 - "APIClient"
Cohesion: 0.17
Nodes (7): APIClient, APIError, badResponse, .errorDescription, server, unauthorized, Person

### Community 119 - "Foundation"
Cohesion: 0.07
Nodes (12): AudioToolbox, AVFoundation, Foundation, ImageIO, AudioSessionPolicy, ImagePrep, MWDATCamera, MWDATCore (+4 more)

### Community 120 - "Earcon"
Cohesion: 0.13
Nodes (14): Earcons, Earcon, cancel, done, error, shutter, sidekickCue, sidekickOff (+6 more)

### Community 125 - "worker.py"
Cohesion: 0.16
Nodes (10): BuildJobsTests, build_jobs(), _recover_stuck_tasks(), _run_check_for_responsibilities(), _run_check_for_stale_conversations(), _run_deliver_pending_updates(), _run_process_conversations(), _run_scheduled_tasks() (+2 more)

### Community 126 - "ConversationController"
Cohesion: 0.09
Nodes (17): Capture, ConversationController, .idleMessage, .isEnabled, .isWorking, .wakeWatching, Once, PhotoSlot (+9 more)

### Community 127 - "Qwen3-TTS: Nova's local TTS fallback"
Cohesion: 0.22
Nodes (8): CustomVoice, not Base, Env vars, How generation works (and its latency), Install (Windows tower), Qwen3-TTS: Nova's local TTS fallback, Smoke test, What wasn't verified, Why it's here

### Community 128 - "agent_loop.py"
Cohesion: 0.10
Nodes (11): PromptSourceEnum, MessageRole, ToolUseStarted, TurnStream, FakeProjectDao, AgentLoopMcpTests, FakeMessage, FakeTextBlock (+3 more)

### Community 132 - "sessions.py"
Cohesion: 0.18
Nodes (4): _as_int(), _flatten(), _is_prose(), _ms_to_iso()

### Community 135 - "history_compaction.py"
Cohesion: 0.20
Nodes (15): _block_chars(), cap_messages(), clear_old_tool_results(), _clearable_blocks(), compact_history(), _env_int(), _is_plain_user_turn(), _history() (+7 more)

### Community 136 - "ToolExecutionError"
Cohesion: 0.24
Nodes (4): main(), main(), main(), ToolExecutionError

### Community 137 - "SidekickConnection"
Cohesion: 0.16
Nodes (3): Utterances, sidekick_socket(), SidekickConnection

### Community 139 - "AudioRouteManager"
Cohesion: 0.22
Nodes (3): AudioRouteManager, Route, .summary

### Community 141 - "run_migrations.py"
Cohesion: 0.16
Nodes (4): main(), migration_files(), _jsonable(), SQLService

### Community 142 - "SpokenProse"
Cohesion: 0.19
Nodes (3): SpokenProse, _said(), SpokenProseTests

### Community 144 - ".setUp"
Cohesion: 0.17
Nodes (8): fake_get_response(), FakeConversationService, FakeMessage, FakeTextBlock, FakeToolDao, FakeUpdateService, fake_get_response(), _schema_tool()

### Community 148 - "._conversation_turn"
Cohesion: 0.09
Nodes (6): deliver(), mark_first_speech(), persist(), _memory_block_budget_seconds(), strip_expects_reply(), _strip_expects_reply_events()

### Community 150 - "SpokenTrackTests"
Cohesion: 0.23
Nodes (3): FakeToolUseBlock, SpokenTrackTests, fake_stream()

### Community 153 - "ToolService"
Cohesion: 0.15
Nodes (5): ToolService, FakeConversationService, FakeToolDao, GlassesCannotRecordMeetingsTests, get_all()

### Community 154 - ".conversation_loop_events"
Cohesion: 0.13
Nodes (9): CountingService, PrefetchedConversationTests, fake_stream(), fake_stream(), fake_stream(), fake_stream(), fake_stream(), FakeBlock (+1 more)

### Community 155 - "NovaGlasses"
Cohesion: 0.29
Nodes (6): Build and test (CLI), Code map, How it behaves, Install on your iPhone, NovaGlasses, On-device field checklist

### Community 156 - "test_process_supervisor.py"
Cohesion: 0.13
Nodes (4): fetch(), main(), sha256(), MirrorTests

### Community 158 - "PassSentinelTests"
Cohesion: 0.09
Nodes (11): is_sidekick_pass(), _agent_loop(), FakeMessage, FakeTextBlock, FakeToolDao, FakeToolUseBlock, _live(), get_final_message() (+3 more)

### Community 159 - "Rig"
Cohesion: 0.18
Nodes (3): Rig, SidekickControllerTests, SidekickEventCodingTests

### Community 161 - "asyncio"
Cohesion: 0.04
Nodes (37): _allowed_origins(), lifespan(), _client_ip(), current_session(), list_sessions(), login(), logout(), logout_all() (+29 more)

### Community 165 - "settings_controller.py"
Cohesion: 0.11
Nodes (6): get_all_settings(), get_available_models(), get_claude_credits(), ModelSwitchRequest, set_model(), ClaudeCreditsService

### Community 170 - "worktree.py"
Cohesion: 0.23
Nodes (7): create(), _git(), remove(), resolve_repo(), slugify(), Workspace, WorktreeError

### Community 172 - "FakeHttp"
Cohesion: 0.25
Nodes (4): build_service(), FakeHttp, InfobipRequestTests, SendSmsTests

### Community 175 - "CooldownTests"
Cohesion: 0.13
Nodes (4): CooldownTests, refused(), _mock_chain(), QwenTTSFallthroughTests

### Community 176 - "BipService"
Cohesion: 0.17
Nodes (3): BipService, _describe_response_error(), _parse_number_list()

### Community 177 - "prepare"
Cohesion: 0.14
Nodes (6): Identification, prepare(), FakeFaceService, jpeg(), PrepareTests, VisionRoutesTests

### Community 178 - ".test_a_live_turn_reads_deltas_then_exposes_the_message"
Cohesion: 0.13
Nodes (4): TurnStreamTests, get_final_message(), __iter__(), get_final_message()

### Community 179 - "Hosting Nova off the home network"
Cohesion: 0.21
Nodes (13): Hosting Nova off the home network, Backend environment variables, Cloudflare Tunnel (nova-tower, cloudflared), Firebase Hosting frontend (nova-voice-nd.web.app), Infobip SMS integration (/sms/inbound), Failed-login lockout policy, Mac coding agent (/ws/coding), MCP OAuth callback (+5 more)

### Community 180 - "os"
Cohesion: 0.06
Nodes (22): _build_file_logger(), _default_log_path(), _timing_enabled(), _env_flag(), _maybe_dump_request(), _describe_failure(), _attn_implementation(), _device_map() (+14 more)

### Community 181 - "AddPersonView"
Cohesion: 0.15
Nodes (7): .api, VisionClient, AddPersonView, .body, FacesView, .body, PhotosUI

### Community 183 - ".setUp"
Cohesion: 0.12
Nodes (4): DirectTurnCounterTests, fake_transcribe(), FakeGate, FakeSidekickLoop

### Community 184 - "conversation_controller.py"
Cohesion: 0.27
Nodes (5): close_conversation(), get_conversation(), get_conversation_messages(), _parse_uuid(), _project_payload()

### Community 185 - ".look"
Cohesion: 0.16
Nodes (11): Vision: "Hey Nova, what do you see?", Client → server, Connecting, Deviations from the brief and additions, Interjections, Prompt and tools, Server behaviour, Server → client (+3 more)

### Community 186 - "replay_request.py"
Cohesion: 0.26
Nodes (5): main(), one_call(), main(), one_call(), variants()

### Community 188 - "endpointing_service.py"
Cohesion: 0.19
Nodes (4): endpoint_decision(), _endpoint_scale(), EndpointDecision, silence_budget_ms()

### Community 190 - "dict"
Cohesion: 0.25
Nodes (3): basic(), InboundSecretTests, RecipientAllowlistTests

### Community 192 - "XCTestCase"
Cohesion: 0.10
Nodes (7): AudioSessionPolicyTests, AmbientForwardingTests, WakePhraseAloneTests, WakeStraightToListeningTests, What is verified and what is not, NovaGlasses, XCTest

### Community 196 - "InterruptedToolCallTests"
Cohesion: 0.19
Nodes (3): InterruptedToolCallTests, fake_stream(), _call()

### Community 201 - "BaseDao"
Cohesion: 0.14
Nodes (3): BaseDao, MessageDao, Message

### Community 207 - "_FakeTable"
Cohesion: 0.17
Nodes (3): _FakeResponse, _FakeSupabaseClient, _FakeTable

### Community 208 - "shell.py"
Cohesion: 0.27
Nodes (5): classify(), _clip(), _resolve_cwd(), run(), _scratch_pair()

### Community 209 - "ConversationTurnMcpDisabledReplayTests"
Cohesion: 0.18
Nodes (4): ConversationTurnMcpDisabledReplayTests, FakeConversationService, FakeMcpService, FakeToolDao

### Community 212 - "protocol.py"
Cohesion: 0.39
Nodes (3): _artifact_for(), encode(), _truncate()

### Community 218 - "Phase"
Cohesion: 0.29
Nodes (7): Phase, idle, listening, off, sentryBlocked, speaking, thinking

## Ambiguous Edges - Review These
- `TTS conversion enhancer prompt (empty)` → `Voice mode tone guidelines`  [AMBIGUOUS]
  prompting/tts_conversion_enhancer_prompt.txt · relation: conceptually_related_to

## Knowledge Gaps
- **171 isolated node(s):** `UserNotifications`, `.serverURLString`, `.summary`, `AudioToolbox`, `.count` (+166 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1617 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **100 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `TTS conversion enhancer prompt (empty)` and `Voice mode tone guidelines`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `NovaGlasses` connect `NovaGlasses` to `XCTestCase`, `.look`, `.handle`?**
  _High betweenness centrality (0.311) - this node is a cross-community bridge._
- **Are the 43 inferred relationships involving `AgentLoop` (e.g. with `Server behaviour` and `PromptEnums`) actually correct?**
  _`AgentLoop` has 43 INFERRED edges - model-reasoned connections that need verification._
- **What connects `UserNotifications`, `.serverURLString`, `.summary` to the rest of the system?**
  _171 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Tool` be split into smaller, more focused modules?**
  _Cohesion score 0.13368983957219252 - nodes in this community are weakly interconnected._
- **Why does `Vision: "Hey Nova, what do you see?"` connect `.look` to `NovaGlasses`?**
  _High betweenness centrality (0.311) - this node is a cross-community bridge._
- **Are the 21 inferred relationships involving `Conversation` (e.g. with `_is_stale()` and `ConversationDao`) actually correct?**
  _`Conversation` has 21 INFERRED edges - model-reasoned connections that need verification._