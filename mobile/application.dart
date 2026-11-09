import 'dart:typed_data';
import 'dart:ui';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_storage/firebase_storage.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:flutter_image_compress/flutter_image_compress.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:image_picker/image_picker.dart';
import 'dart:io';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as Path;
import 'package:permission_handler/permission_handler.dart';
import 'package:gallery_saver/gallery_saver.dart';
import 'package:provider/provider.dart'; // Import Provider
import '../app_state.dart'; // Import the file where AppData is defined
import 'package:fluttertoast/fluttertoast.dart';

class ImagePickerApp extends StatefulWidget {
  const ImagePickerApp({Key? key}) : super(key: key);

  @override
  _ImagePickerAppState createState() => _ImagePickerAppState();
}

class _ImagePickerAppState extends State<ImagePickerApp> {
  File? _image;
  String predictionResult = '';
  String connectionStatus = 'Connecting...';
  final int raspberryPiPort = 60001;
  String raspberryPiIp = '192.168.170.35';
  // Change this URL to your Flutter app's URL
  final String flutterAppUrl = 'https://obliging-fine-mantis.ngrok-free.app';
  bool isLoading = false;
  bool isRaspberryPiConnected = false;

  Future getImage(ImageSource source) async {
    try {
      final image = await ImagePicker().pickImage(source: source);
      if (image == null) return;

      final imagePermanent = await saveFilePermanently(image.path);

      setState(() {
        this._image = imagePermanent;
      });
      if (_image != null) {
        await uploadImageToFirebase(_image!);
      }
      // Call _uploadImage function to upload the image to the server
      await _uploadImage(_image!);
      // await makePrediction(_image!.path);
    } on Exception catch (e) {
      print('Failed to pick image: $e');
    }
  }

  Future<File> saveFilePermanently(String imagePath) async {
    final directory = await getApplicationDocumentsDirectory();
    final name = Path.basename(imagePath);
    final image = File('${directory.path}/$name');

    return File(imagePath).copy(image.path);
  }

  Future<void> _uploadImage(File imageFile) async {
    if (imageFile == null) {
      print('Image file is null');
      return;
    }

    // Save the image with the name "test" for prediction
    final newFilePath = '${imageFile.parent.path}/test1.jpg';
    await imageFile.copy(newFilePath);

    // Upload the original image to Firebase
    await uploadImageToFirebase(imageFile);

    final url = Uri.parse('$flutterAppUrl/predict');

    try {
      final request = http.MultipartRequest('POST', url)
        ..files.add(
          await http.MultipartFile.fromPath('image', newFilePath),
        )
        ..fields['image_path'] = newFilePath; // Include image path in JSON data

      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        print("Image uploaded to server successfully.");
        print(response.body);
        Map<String, dynamic> responseJson = json.decode(response.body);
        dynamic prediction = responseJson['prediction'];
        print(prediction);
        // Call makePrediction with the file path
        // await makePrediction(newFilePath);
      } else {
        print("Failed to upload image to server: ${response.statusCode}");
      }
    } catch (e) {
      print('Error uploading image to server: $e');
    }
  }

  // Future<void> makePrediction(String imagePath) async {
  //   final String apiUrl = '$flutterAppUrl/predict';
  //   final Uri uri = Uri.parse(apiUrl);
  //
  //   try {
  //     final response = await http.post(
  //       uri,
  //       headers: {'Content-Type': 'application/json'},
  //       body: jsonEncode({'image_path': imagePath}),
  //     );
  //
  //     if (response.statusCode == 200) {
  //       print(response.body);
  //       // Map<String, dynamic> responseJson = json.decode(response.body);
  //       // dynamic prediction = responseJson['prediction'];
  //
  //       setState(() {
  //         predictionResult = response.body;
  //       });
  //     } else {
  //       throw Exception('Failed to make a prediction.');
  //     }
  //   } catch (e) {
  //     print('Failed to make a prediction: $e');
  //   }
  // }

  Future<void> uploadImageToFirebase(File imageFile) async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return;

    final email = user.email;
    final storageReference = FirebaseStorage.instance.ref().child(
        'user_images/$email/${DateTime.now().millisecondsSinceEpoch}.jpg');

    final UploadTask uploadTask = storageReference.putFile(imageFile);

    await uploadTask.whenComplete(() {
      print('Image uploaded');
      Fluttertoast.showToast(
        msg: "Image uploaded to Database", // Your toast message
        toastLength: Toast.LENGTH_SHORT,
        gravity: ToastGravity.BOTTOM,
        timeInSecForIosWeb: 1,
        backgroundColor: Colors.green,
        textColor: Colors.white,
        fontSize: 16.0,
      );
    });

    final imageUrl = await storageReference.getDownloadURL();
    print('Image URL: $imageUrl');
  }

  Future<void> initiateRaspberryPiConnection() async {
    try {
      setState(() {
        isLoading = true; // Show the loading indicator
      });

      final Socket socket =
          await Socket.connect(raspberryPiIp, raspberryPiPort);
      print('Connected to Raspberry Pi for image transfer');
      setState(() {
        isRaspberryPiConnected = true;
      });

      final Directory appDocDir = await getApplicationDocumentsDirectory();
      final String filePath = '${appDocDir.path}/received_image.jpg';
      final File receivedFile = File(filePath);

      try {
        IOSink fileSink = receivedFile.openWrite();
        int totalBytesReceived = 0;

        socket.listen(
          (List<int> data) {
            totalBytesReceived += data.length;
            fileSink.add(data);
          },
          onDone: () async {
            print('Image received successfully');
            fileSink.close();
            socket.close();

            // Show a toast notification
            Fluttertoast.showToast(
              msg: "Image(s) Received",
              toastLength: Toast.LENGTH_SHORT,
              gravity: ToastGravity.BOTTOM,
              timeInSecForIosWeb: 1,
              backgroundColor: Colors.green,
              textColor: Colors.white,
              fontSize: 16.0,
            );

            // Save the image to the gallery
            final permissionStatus = await Permission.storage.request();
            if (permissionStatus.isGranted) {
              final bool? isSaved =
                  await GallerySaver.saveImage(receivedFile.path);
              if (isSaved != null) {
                if (isSaved) {
                  print('Image saved to gallery.');
                } else {
                  print('Failed to save the image to gallery.');
                }
              } else {
                print('Error: The result of saving the image is null.');
              }
            } else {
              print("Permission to access storage denied");
            }

            setState(() {
              isLoading = false; // Hide the loading indicator
              isRaspberryPiConnected = false; // The connection is removed
            });
          },
          onError: (e) {
            print('Error: $e');
            fileSink.close();
            socket.close();
          },
        );
      } catch (e) {
        print('Error: $e');
        socket.close();
      }
    } catch (e) {
      print('Error connecting to Raspberry Pi: $e');
    }
  }

  Future<String> saveReceivedImage(Uint8List imageBytes) async {
    final String fileName = "received_image.jpg";
    final Directory directory = await getApplicationDocumentsDirectory();
    final String filePath = '${directory.path}/$fileName';

    final File imageFile = File(filePath);
    await imageFile.writeAsBytes(imageBytes);

    // Save the image to the gallery
    await GallerySaver.saveImage(imageFile.path);

    print("Image saved to gallery and local storage: $filePath");

    return filePath;
  }

  @override
  void initState() {
    super.initState();
  }

  @override
  Widget build(BuildContext context) {
    final appData = Provider.of<AppData>(context); // Access the provider

    // Set the raspberryPiIp using the appData.ipAddress
    raspberryPiIp = appData.ipAddress;
    return SafeArea(
      child: Scaffold(
        // appBar: AppBar(
        //   title: Text("C A M E R A"),
        //   backgroundColor: Colors.deepPurple,
        //   automaticallyImplyLeading: false,
        // ),
        body: Container(
          height: double.infinity,
          decoration: BoxDecoration(
            image: DecorationImage(
              image: AssetImage("images/abstract3.jpg"),
              fit: BoxFit.cover,
            ),
          ),
          child: BackdropFilter(
            filter: ImageFilter.blur(sigmaX: 10.0, sigmaY: 10.0),
            child: SingleChildScrollView(
              child: Center(
                child: Column(
                  children: [
                    SizedBox(
                      height: 100,
                    ),
                    _image != null
                        ? Image.file(
                            _image!,
                            width: 250,
                            height: 250,
                            fit: BoxFit.cover,
                          )
                        : Image.asset(
                            "images/eye.jpg",
                            height: 200,
                          ),
                    SizedBox(
                      height: 20,
                    ),
                    SizedBox(height: 40),
                    Padding(
                      padding: const EdgeInsets.all(10),
                      child: SizedBox(
                        width: double.infinity,
                        child: Material(
                          elevation: 30,
                          color: Colors.red[300],
                          borderRadius: BorderRadius.circular(10),
                          child: InkWell(
                            onTap: () => getImage(ImageSource.gallery),
                            child: Padding(
                              padding: EdgeInsets.symmetric(
                                  vertical: 15, horizontal: 40),
                              child: Center(
                                child: Text(
                                  "Pick from Gallery",
                                  style: TextStyle(
                                    color: Colors.white,
                                    fontSize: 25,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                    SizedBox(
                      height: 0,
                    ),
                    Padding(
                      padding: const EdgeInsets.all(10),
                      child: SizedBox(
                        width: double.infinity,
                        child: Material(
                          elevation: 30,
                          color: Colors.red[300],
                          borderRadius: BorderRadius.circular(10),
                          child: InkWell(
                            onTap: () => getImage(ImageSource.camera),
                            child: Padding(
                              padding: EdgeInsets.symmetric(
                                  vertical: 15, horizontal: 40),
                              child: Center(
                                child: Text(
                                  "Pick from Camera",
                                  style: TextStyle(
                                    color: Colors.white,
                                    fontSize: 25,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                    SizedBox(height: 20),
                    // Text(
                    //   'Prediction Result:',
                    //   style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                    // ),
                    // Text(
                    //   predictionResult,
                    //   style: TextStyle(fontSize: 16),
                    // ),
                    SizedBox(height: 20),
                    if (isLoading)
                      CircularProgressIndicator(), // Show loading indicator if isLoading is true
                    if (!isRaspberryPiConnected) // Show the connect button when not connected
                      Padding(
                        padding: const EdgeInsets.all(10),
                        child: SizedBox(
                          width: 310,
                          child: Material(
                            elevation: 30,
                            color: Colors.red[300],
                            borderRadius: BorderRadius.circular(10),
                            child: InkWell(
                              onTap: () => initiateRaspberryPiConnection(),
                              child: Padding(
                                padding: EdgeInsets.symmetric(
                                    vertical: 15, horizontal: 40),
                                child: Center(
                                  child: Row(
                                    children: [
                                      Text(
                                        "Receive image",
                                        style: TextStyle(
                                          color: Colors.white,
                                          fontSize: 25,
                                          fontWeight: FontWeight.bold,
                                        ),
                                      ),
                                      SizedBox(width: 10),
                                      Icon(
                                        Icons
                                            .compare_arrows_rounded, // Use the compare arrows icon
                                        color: Colors.white,
                                        size: 35, // Adjust the size as needed
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                    // ElevatedButton(
                    //   onPressed: () {
                    //     initiateRaspberryPiConnection();
                    //   },
                    //   child: Text('Receive Image'),
                    // ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
