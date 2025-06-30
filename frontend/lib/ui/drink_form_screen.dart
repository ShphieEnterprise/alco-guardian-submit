import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter/cupertino.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

class DrinkFormScreen extends StatefulWidget {
  const DrinkFormScreen({super.key});

  @override
  State<DrinkFormScreen> createState() => _DrinkFormScreenState();
}

class _DrinkFormScreenState extends State<DrinkFormScreen> {
  final _formKey = GlobalKey<FormState>();
  final _alcoholPercentageController = TextEditingController();
  final _volumeController = TextEditingController();
  
  String _selectedDrinkType = 'ビール';
  bool _isSubmitting = false;

  final List<String> _drinkTypes = ['ビール', 'ハイボール', 'その他'];

  void _showDrinkTypePicker(BuildContext context) {
    showCupertinoModalPopup(
      context: context,
      builder: (BuildContext context) {
        return Container(
          height: 250,
          color: CupertinoColors.systemBackground.resolveFrom(context),
          child: Column(
            children: [
              Container(
                height: 50,
                color: CupertinoColors.systemBackground.resolveFrom(context),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    CupertinoButton(
                      child: const Text('キャンセル'),
                      onPressed: () {
                        Navigator.pop(context);
                      },
                    ),
                    CupertinoButton(
                      child: const Text('完了'),
                      onPressed: () {
                        Navigator.pop(context);
                      },
                    ),
                  ],
                ),
              ),
              Expanded(
                child: CupertinoPicker(
                  backgroundColor: CupertinoColors.systemBackground.resolveFrom(context),
                  itemExtent: 40,
                  onSelectedItemChanged: (int index) {
                    setState(() {
                      _selectedDrinkType = _drinkTypes[index];
                    });
                  },
                  scrollController: FixedExtentScrollController(
                    initialItem: _drinkTypes.indexOf(_selectedDrinkType),
                  ),
                  children: _drinkTypes.map((String type) {
                    return Center(child: Text(type));
                  }).toList(),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  @override
  void dispose() {
    _alcoholPercentageController.dispose();
    _volumeController.dispose();
    super.dispose();
  }

  Future<void> _submitDrinkRecord() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    setState(() {
      _isSubmitting = true;
    });

    try {
      final response = await http.post(
        Uri.parse('https://asia-northeast1-alco-guardian.cloudfunctions.net/drink'),
        headers: {
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'drinkType': _selectedDrinkType,
          'alcoholPercentage': double.parse(_alcoholPercentageController.text),
          'volume': double.parse(_volumeController.text),
        }),
      );

      if (response.statusCode == 200) {
        final responseData = jsonDecode(response.body);
        if (responseData['success'] == true) {
          if (mounted) {
            // Navigate back to previous screen (chat/home) with response data
            Navigator.pop(context, responseData);
          }
        } else {
          throw Exception('Failed to record drink');
        }
      } else {
        throw Exception('Failed to record drink');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('エラーが発生しました: ${e.toString()}'),
            backgroundColor: Colors.red,
            duration: const Duration(seconds: 5), // Show error longer
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isSubmitting = false;
        });
      }
    }
  }


  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final isIOS = Theme.of(context).platform == TargetPlatform.iOS;
    final keyboardHeight = MediaQuery.of(context).viewInsets.bottom;

    return GestureDetector(
      onTap: () {
        // Dismiss keyboard when tapping outside
        FocusScope.of(context).unfocus();
      },
      child: Scaffold(
        resizeToAvoidBottomInset: true,
        appBar: AppBar(
          title: const Text('飲酒記録'),
          backgroundColor: isIOS ? null : colorScheme.primaryContainer,
          foregroundColor: isIOS ? null : colorScheme.onPrimaryContainer,
          elevation: isIOS ? 0 : null,
          scrolledUnderElevation: isIOS ? 0 : null,
        ),
        body: SafeArea(
          child: Form(
            key: _formKey,
            child: SingleChildScrollView(
              padding: EdgeInsets.only(
                left: 16.0,
                right: 16.0,
                top: 16.0,
                bottom: keyboardHeight > 0 ? 16.0 : 32.0,
              ),
              keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '飲んだお酒を記録しましょう',
                    style: theme.textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 24),
                  
                  // Drink Type Selection
                  Text(
                    'お酒の種類',
                    style: theme.textTheme.titleMedium,
                  ),
                  const SizedBox(height: 8),
                  isIOS
                      ? GestureDetector(
                          onTap: () {
                            _showDrinkTypePicker(context);
                          },
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                            decoration: BoxDecoration(
                              color: colorScheme.surfaceContainerHighest,
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(
                                color: colorScheme.outline.withValues(alpha: 0.5),
                              ),
                            ),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text(
                                  _selectedDrinkType,
                                  style: theme.textTheme.bodyLarge,
                                ),
                                Icon(
                                  CupertinoIcons.chevron_down,
                                  size: 20,
                                  color: colorScheme.onSurfaceVariant,
                                ),
                              ],
                            ),
                          ),
                        )
                      : DropdownButtonFormField<String>(
                          value: _selectedDrinkType,
                          decoration: InputDecoration(
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12),
                            ),
                            filled: true,
                            fillColor: colorScheme.surfaceContainerHighest,
                          ),
                          items: _drinkTypes.map((String type) {
                            return DropdownMenuItem<String>(
                              value: type,
                              child: Text(type),
                            );
                          }).toList(),
                          onChanged: (String? newValue) {
                            setState(() {
                              _selectedDrinkType = newValue!;
                            });
                          },
                        ),
                  const SizedBox(height: 24),
                  
                  // Alcohol Percentage Input
                  Text(
                    'アルコール度数 (%)',
                    style: theme.textTheme.titleMedium,
                  ),
                  const SizedBox(height: 8),
                  TextFormField(
                    controller: _alcoholPercentageController,
                    decoration: InputDecoration(
                      hintText: '例: 5.0',
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                      filled: true,
                      fillColor: colorScheme.surfaceContainerHighest,
                      suffixText: '%',
                    ),
                    keyboardType: const TextInputType.numberWithOptions(decimal: true, signed: false),
                    textInputAction: TextInputAction.next,
                    inputFormatters: [
                      FilteringTextInputFormatter.allow(RegExp(r'^\d*\.?\d*')),
                      // iOS specific: limit to 2 decimal places
                      TextInputFormatter.withFunction((oldValue, newValue) {
                        final text = newValue.text;
                        if (text.contains('.')) {
                          final parts = text.split('.');
                          if (parts.length > 1 && parts[1].length > 2) {
                            return oldValue;
                          }
                        }
                        return newValue;
                      }),
                    ],
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return 'アルコール度数を入力してください';
                      }
                      final percentage = double.tryParse(value);
                      if (percentage == null || percentage < 0 || percentage > 100) {
                        return '0〜100の数値を入力してください';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 24),
                  
                  // Volume Input
                  Text(
                    '飲酒量 (ml)',
                    style: theme.textTheme.titleMedium,
                  ),
                  const SizedBox(height: 8),
                  TextFormField(
                    controller: _volumeController,
                    decoration: InputDecoration(
                      hintText: '例: 350',
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                      filled: true,
                      fillColor: colorScheme.surfaceContainerHighest,
                      suffixText: 'ml',
                    ),
                    keyboardType: const TextInputType.numberWithOptions(decimal: true, signed: false),
                    textInputAction: TextInputAction.done,
                    onFieldSubmitted: (_) {
                      if (!_isSubmitting) {
                        _submitDrinkRecord();
                      }
                    },
                    inputFormatters: [
                      FilteringTextInputFormatter.allow(RegExp(r'^\d*\.?\d*')),
                      // iOS specific: limit to 1 decimal place for volume
                      TextInputFormatter.withFunction((oldValue, newValue) {
                        final text = newValue.text;
                        if (text.contains('.')) {
                          final parts = text.split('.');
                          if (parts.length > 1 && parts[1].length > 1) {
                            return oldValue;
                          }
                        }
                        return newValue;
                      }),
                    ],
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return '飲酒量を入力してください';
                      }
                      final volume = double.tryParse(value);
                      if (volume == null || volume <= 0) {
                        return '正しい飲酒量を入力してください';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 32),
                  
                  // Submit Button
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton(
                      onPressed: _isSubmitting ? null : _submitDrinkRecord,
                      style: FilledButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                      child: _isSubmitting
                          ? const SizedBox(
                              height: 20,
                              width: 20,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                color: Colors.white,
                              ),
                            )
                          : const Text(
                              '記録する',
                              style: TextStyle(fontSize: 16),
                            ),
                    ),
                  ),
                  // Add extra padding at bottom for iOS
                  if (isIOS) const SizedBox(height: 20),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}