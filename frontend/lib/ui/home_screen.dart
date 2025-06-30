import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'dart:math' as math;
import '../models/record_state.dart';
import '../models/chat_message.dart';
import '../services/recorder_service.dart';
import '../services/auth/firebase_auth_service.dart';
import '../services/chat_service.dart';
import '../services/player_service.dart';
import 'profile_screen.dart';
import 'drink_form_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> with SingleTickerProviderStateMixin {
  final _recorder = RecorderService();
  final _authService = FirebaseAuthService();
  final _chatService = ChatService();
  late final _playerService = PlayerService(recorderService: _recorder);
  RecordStatus status = RecordStatus.idle;
  String? filePath;
  User? currentUser;
  bool _isInitialized = false;
  bool _initializationFailed = false;
  bool _isTranscribing = false;
  bool _isChatting = false;
  List<ChatMessage> _chatMessages = [];
  final ScrollController _scrollController = ScrollController();
  late AnimationController _animationController;
  late Animation<double> _pulseAnimation;
  String? _currentImagePath;

  @override
  void initState() {
    super.initState();
    currentUser = _authService.currentUser;
    _initializeServices();
    _loadInitialImage();

    // Initialize animation controller
    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    );
    _pulseAnimation = Tween<double>(begin: 1.0, end: 1.2).animate(
      CurvedAnimation(
        parent: _animationController,
        curve: Curves.easeInOut,
      ),
    );
    // Repeat animation for recording state
    _animationController.addStatusListener((status) {
      if (status == AnimationStatus.completed) {
        _animationController.reverse();
      } else if (status == AnimationStatus.dismissed) {
        _animationController.forward();
      }
    });
  }

  Future<void> _initializeServices() async {
    try {
      setState(() {
        _initializationFailed = false;
      });
      await _recorder.init();
      await _playerService.init();
      setState(() {
        _isInitialized = true;
      });
      print('WebRecorder初期化成功');
    } catch (e) {
      print('初期化エラー: $e');
      setState(() {
        _initializationFailed = true;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('録音機能の初期化に失敗しました。マイクの許可が必要です。'),
            action: SnackBarAction(
              label: '再試行',
              onPressed: _initializeServices,
            ),
          ),
        );
      }
    }
  }

  @override
  void dispose() {
    _animationController.dispose();
    _scrollController.dispose();
    _recorder.dispose();
    _playerService.dispose();
    super.dispose();
  }

  void _handleRecordingAction() async {
    if (_initializationFailed) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text('録音機能の初期化に失敗しています'),
          action: SnackBarAction(
            label: '再試行',
            onPressed: _initializeServices,
          ),
        ),
      );
      return;
    }
    
    if (!_isInitialized) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('録音機能を初期化中です...')),
      );
      return;
    }
    
    try {
      switch (status) {
        case RecordStatus.idle:
          filePath = await _recorder.start();
          setState(() => status = RecordStatus.recording);
          _animationController.forward();
          break;
        case RecordStatus.recording:
          await _recorder.stop();
          setState(() => status = RecordStatus.playbackReady);
          _animationController.stop();
          _animationController.reset();
          // 録音停止後、自動的にワークフローを開始
          await _autoProcessRecording();
          break;
        case RecordStatus.playbackReady:
          // 既に自動処理が完了し、新しい録音の準備ができている
          filePath = await _recorder.start();
          setState(() => status = RecordStatus.recording);
          _animationController.forward();
          break;
      }
    } catch (e) {
      // エラーハンドリング
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('録音エラー: $e')),
      );
      setState(() => status = RecordStatus.idle);
      _animationController.stop();
      _animationController.reset();
    }
  }

  String _getStatusText() {
    switch (status) {
      case RecordStatus.idle:
        return '録音を開始するにはタップしてください';
      case RecordStatus.recording:
        return '録音中...';
      case RecordStatus.playbackReady:
        if (_isTranscribing) {
          return '音声を転写中...';
        } else if (_isChatting) {
          return 'Bartenderとチャット中...';
        } else {
          return 'タップして続けて録音';
        }
    }
  }

  Future<void> _autoProcessRecording() async {
    try {
      // 1. 転写処理
      final transcriptionResult = await _transcribeAudio();
      
      // 2. 転写結果があればユーザーメッセージとして追加
      if (transcriptionResult != null && transcriptionResult.isNotEmpty) {
        setState(() {
          _chatMessages.add(ChatMessage.user(transcriptionResult));
        });
        _scrollToBottom();
        
        // 3. チャット処理
        final chatResponse = await _sendToChat(transcriptionResult);
        
        // 4. Bartenderの返答を履歴に追加
        if (chatResponse != null) {
          setState(() {
            _chatMessages.add(ChatMessage.bartender(
              chatResponse.message,
              audioUrl: chatResponse.audioUrl,
            ));
          });
          _scrollToBottom();
          
          // 5. 音声URLがあれば自動再生
          if (chatResponse.audioUrl != null) {
            _loadRandomImage();
            await _playAudioFromUrl(chatResponse.audioUrl!);
          }
        }
      }
      
      // 処理完了後、新しい録音の準備完了状態に
      setState(() {
        status = RecordStatus.playbackReady;
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('自動処理エラー: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _playAudioFromUrl(String audioUrl) async {
    try {
      await _playerService.playFromUrl(audioUrl);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('音声再生エラー: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  void _handleDrinkResponse(Map<String, dynamic> responseData) {
    final message = responseData['message'] ?? '';
    final audioUrl = responseData['audioUrl'];
    final guardian = responseData['guardian'];
    final guardianLevel = guardian?['level'];
    final levelColor = guardianLevel?['color'] ?? 'green';
    final levelMessage = guardianLevel?['message'] ?? '';
    
    // Create a combined message with both the response and guardian level
    String fullMessage = message;
    if (levelMessage.isNotEmpty && levelMessage != '監視中') {
      fullMessage += '\n\n🛡️ $levelMessage';
    }
    
    // Add message to chat
    final chatMessage = ChatMessage.bartender(
      fullMessage,
      audioUrl: audioUrl,
      guardianColor: levelColor,
    );
    
    setState(() {
      _chatMessages.add(chatMessage);
    });
    
    // Auto-scroll to bottom
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
    
    // Auto-play audio if available
    if (audioUrl != null) {
      _loadRandomImage();
      _playAudioFromUrl(audioUrl);
    }
  }

  Color _getStatusColor(ColorScheme colorScheme) {
    switch (status) {
      case RecordStatus.idle:
        return colorScheme.primary;
      case RecordStatus.recording:
        return Colors.red;
      case RecordStatus.playbackReady:
        return colorScheme.primary; // アイドル状態と同じ色に変更
    }
  }

  Color _getGuardianColor(String? guardianColor) {
    switch (guardianColor) {
      case 'red':
        return Colors.red.shade600;
      case 'yellow':
        return Colors.amber.shade600;
      case 'green':
        return Colors.green.shade600;
      default:
        return Colors.blue.shade600; // Default for regular bartender messages
    }
  }

  IconData _getGuardianIcon(String? guardianColor) {
    switch (guardianColor) {
      case 'red':
        return Icons.warning; // Warning icon for red level
      case 'yellow':
        return Icons.info; // Info icon for yellow level
      case 'green':
        return Icons.check_circle; // Check circle for green level
      default:
        return Icons.local_bar; // Default bartender icon
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: Text(
          'Alco Guardian',
          style: theme.textTheme.titleLarge?.copyWith(
            fontWeight: FontWeight.bold,
            color: colorScheme.primary,
          ),
        ),
        centerTitle: true,
        elevation: 0,
        backgroundColor: Colors.transparent,
        actions: [
          IconButton(
            icon: Icon(
              Icons.local_bar,
              color: colorScheme.primary,
              size: 28,
            ),
            onPressed: () async {
              final result = await Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => const DrinkFormScreen(),
                ),
              );
              
              // Handle response from drink form
              if (result != null && mounted) {
                _handleDrinkResponse(result);
              }
            },
          ),
          IconButton(
            icon: Icon(
              Icons.account_circle_outlined,
              color: colorScheme.primary,
              size: 28,
            ),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => const ProfileScreen(),
                ),
              );
            },
          ),
        ],
      ),
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              colorScheme.background,
              colorScheme.primaryContainer.withOpacity(0.2),
            ],
          ),
        ),
        child: SafeArea(
          bottom: false, // FloatingActionButtonのためにbottomは除外
          child: Column(
            children: [
              // Image display area (upper half)
              Expanded(
                flex: 1,
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Center(
                    child: Container(
                      constraints: const BoxConstraints(
                        maxWidth: 400,
                        maxHeight: 300,
                      ),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(12),
                        color: colorScheme.surface,
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withOpacity(0.1),
                            blurRadius: 8,
                            offset: const Offset(0, 4),
                          ),
                        ],
                      ),
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(12),
                        child: _currentImagePath != null
                            ? Image.asset(
                                _currentImagePath!,
                                fit: BoxFit.contain,
                                errorBuilder: (context, error, stackTrace) {
                                  return Container(
                                    color: colorScheme.surfaceContainerLow,
                                    child: const Center(
                                      child: Icon(
                                        Icons.image_not_supported,
                                        size: 48,
                                        color: Colors.grey,
                                      ),
                                    ),
                                  );
                                },
                              )
                            : Container(
                                color: colorScheme.surfaceContainerLow,
                                child: const Center(
                                  child: CircularProgressIndicator(),
                                ),
                              ),
                      ),
                    ),
                  ),
                ),
              ),

              // Chat area (lower half)
              Expanded(
                flex: 1,
                child: Column(
                  children: [
                    // Status card
                    Padding(
                      padding: const EdgeInsets.fromLTRB(16.0, 0, 16.0, 8.0),
                      child: Card(
                        elevation: 0,
                        color: colorScheme.surface,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(16),
                          side: BorderSide(
                            color: colorScheme.outlineVariant.withOpacity(0.2),
                            width: 1,
                          ),
                        ),
                        child: Padding(
                          padding: const EdgeInsets.all(16.0),
                          child: Row(
                            children: [
                              CircleAvatar(
                                backgroundColor: colorScheme.primaryContainer,
                                radius: 20,
                                child: Icon(
                                  Icons.person,
                                  color: colorScheme.onPrimaryContainer,
                                  size: 20,
                                ),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Text(
                                  'マイクボタンを押して話しかけてみてね！',
                                  style: theme.textTheme.titleSmall?.copyWith(
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),

                    // Chat history
                    Expanded(
                      child: Padding(
                        padding: const EdgeInsets.only(bottom: 80.0), // マイクボタン分のスペースを確保
                        child: _chatMessages.isEmpty
                          ? Center(
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Icon(
                                    Icons.chat_bubble_outline,
                                    size: 48,
                                    color: colorScheme.primary.withValues(alpha: 0.3),
                                  ),
                                  const SizedBox(height: 16),
                                  Text(
                                    '録音してBartenderと会話しましょう',
                                    style: theme.textTheme.bodyMedium?.copyWith(
                                      color: colorScheme.onSurface.withValues(alpha: 0.7),
                                    ),
                                  ),
                                ],
                              ),
                            )
                          : ListView.builder(
                              controller: _scrollController,
                              padding: const EdgeInsets.symmetric(horizontal: 16.0),
                              itemCount: _chatMessages.length,
                              itemBuilder: (context, index) {
                                final message = _chatMessages[index];
                                return _buildChatBubble(context, message, theme, colorScheme);
                              },
                            ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
      floatingActionButton: Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(context).padding.bottom > 0 
              ? 0 // iOSでホームインジケーターがある場合
              : 16, // ホームインジケーターがない場合
        ),
        child: FloatingActionButton(
          onPressed: _handleRecordingAction,
          elevation: 4,
          backgroundColor: _getStatusColor(colorScheme),
          foregroundColor: Colors.white,
          child: Icon(
            status == RecordStatus.recording
                ? Icons.stop
                : Icons.mic,
            size: 24,
          ),
        ),
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerFloat,
    );
  }
  
  
  
  Future<String?> _transcribeAudio() async {
    setState(() {
      _isTranscribing = true;
    });
    
    try {
      final result = await _recorder.transcribeRecording();
      
      if (result['success'] == true) {
        setState(() {
          _isTranscribing = false;
        });
        return result['transcription'];
      } else {
        throw Exception(result['error'] ?? '転写に失敗しました');
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isTranscribing = false;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('転写エラー: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
      return null;
    }
  }

  Future<ChatResponse?> _sendToChat(String message) async {
    setState(() {
      _isChatting = true;
    });
    
    try {
      final chatResponse = await _chatService.sendMessage(message, enableTTS: true);
      
      setState(() {
        _isChatting = false;
      });
      
      return chatResponse;
    } catch (e) {
      if (mounted) {
        setState(() {
          _isChatting = false;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('チャットエラー: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
      return null;
    }
  }

  void _scrollToBottom() {
    if (_scrollController.hasClients) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      });
    }
  }

  void _loadRandomImage() {
    final images = [
      'assets/images/image_1.png',
      'assets/images/image_2.png',
      'assets/images/image_3.png',
      'assets/images/image_4.png',
      'assets/images/image_5.png',
    ];
    
    final random = math.Random();
    setState(() {
      _currentImagePath = images[random.nextInt(images.length)];
    });
  }

  void _loadInitialImage() {
    setState(() {
      _currentImagePath = 'assets/images/image_1.png';
    });
  }

  Widget _buildChatBubble(BuildContext context, ChatMessage message, ThemeData theme, ColorScheme colorScheme) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16.0),
      child: Row(
        mainAxisAlignment: message.isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (!message.isUser) ...[
            CircleAvatar(
              radius: 16,
              backgroundColor: _getGuardianColor(message.guardianColor),
              child: Icon(
                _getGuardianIcon(message.guardianColor),
                size: 16,
                color: Colors.white,
              ),
            ),
            const SizedBox(width: 8),
          ],
          Flexible(
            child: Container(
              constraints: BoxConstraints(
                maxWidth: MediaQuery.of(context).size.width * 0.75,
              ),
              decoration: BoxDecoration(
                color: message.isUser
                    ? colorScheme.primary
                    : colorScheme.surfaceContainerLow,
                borderRadius: BorderRadius.circular(16).copyWith(
                  bottomRight: message.isUser ? const Radius.circular(4) : null,
                  bottomLeft: !message.isUser ? const Radius.circular(4) : null,
                ),
              ),
              padding: const EdgeInsets.all(12.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    message.content,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: message.isUser
                          ? colorScheme.onPrimary
                          : colorScheme.onSurface,
                    ),
                  ),
                  if (!message.isUser && message.audioUrl != null) ...[
                    const SizedBox(height: 8),
                    TextButton.icon(
                      onPressed: () async {
                        await _playAudioFromUrl(message.audioUrl!);
                      },
                      icon: const Icon(Icons.play_arrow, size: 18),
                      label: const Text('音声を再生', style: TextStyle(fontSize: 14)),
                      style: TextButton.styleFrom(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                        minimumSize: const Size(44, 44), // iOSのタップターゲットサイズ
                        tapTargetSize: MaterialTapTargetSize.padded,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
          if (message.isUser) ...[
            const SizedBox(width: 8),
            CircleAvatar(
              radius: 16,
              backgroundColor: colorScheme.primary,
              child: const Icon(
                Icons.person,
                size: 16,
                color: Colors.white,
              ),
            ),
          ],
        ],
      ),
    );
  }

}
