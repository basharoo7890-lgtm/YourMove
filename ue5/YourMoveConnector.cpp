// YourMoveConnector.cpp — aligned with FastAPI app (sessions + websocket routers)

#include "YourMoveConnector.h"
#include "WebSocketsModule.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "Serialization/JsonReader.h"
#include "Dom/JsonObject.h"
#include "Misc/DateTime.h"
#include "HttpModule.h"
#include "Interfaces/IHttpRequest.h"
#include "Interfaces/IHttpResponse.h"
#include "GenericPlatform/GenericPlatformHttp.h"

UYourMoveConnector::UYourMoveConnector()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.TickInterval = 0.0f;
}

void UYourMoveConnector::BeginPlay()
{
	Super::BeginPlay();
	if (!FModuleManager::Get().IsModuleLoaded(TEXT("WebSockets")))
	{
		FModuleManager::Get().LoadModule(TEXT("WebSockets"));
	}
	UE_LOG(LogTemp, Log, TEXT("[YourMove] Connector — Host=%s Port=%d TLS=%s"),
		*ServerHost, ServerPort, bUseTLS ? TEXT("on") : TEXT("off"));
}

void UYourMoveConnector::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	Disconnect();
	Super::EndPlay(EndPlayReason);
}

void UYourMoveConnector::TickComponent(float DeltaTime, ELevelTick TickType,
	FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);

	if (bIsBaselinePhase)
	{
		BaselineElapsed += DeltaTime;
		BaselineTimeRemaining = FMath::Max(0.0f, BaselineDuration - BaselineElapsed);
		if (BaselineElapsed >= BaselineDuration)
		{
			EndBaseline();
		}
	}

	if (bShouldReconnect && ConnectionState == EYourMoveState::Disconnected)
	{
		ReconnectTimer += DeltaTime;
		if (ReconnectTimer >= ReconnectInterval)
		{
			ReconnectTimer = 0.0f;
			UE_LOG(LogTemp, Warning, TEXT("[YourMove] Reconnecting WebSocket..."));
			ConnectWebSocket();
		}
	}
}

FString UYourMoveConnector::BuildHttpBaseUrl() const
{
	const FString Scheme = bUseTLS ? TEXT("https") : TEXT("http");
	const FString Host = ServerHost.TrimStartAndEnd();
	const bool OmitPort = (bUseTLS && ServerPort == 443) || (!bUseTLS && ServerPort == 80);
	if (OmitPort)
	{
		return FString::Printf(TEXT("%s://%s"), *Scheme, *Host);
	}
	return FString::Printf(TEXT("%s://%s:%d"), *Scheme, *Host, ServerPort);
}

FString UYourMoveConnector::BuildWebSocketUrl(const FString& CleanSessionId) const
{
	const FString Scheme = bUseTLS ? TEXT("wss") : TEXT("ws");
	const FString Host = ServerHost.TrimStartAndEnd();
	const bool OmitPort = (bUseTLS && ServerPort == 443) || (!bUseTLS && ServerPort == 80);
	FString Authority = OmitPort ? Host : FString::Printf(TEXT("%s:%d"), *Host, ServerPort);
	const FString EncodedToken = FGenericPlatformHttp::UrlEncode(TherapistJwtToken.TrimStartAndEnd());
	return FString::Printf(TEXT("%s://%s/ws/ue5/%s?token=%s"), *Scheme, *Authority, *CleanSessionId, *EncodedToken);
}

bool UYourMoveConnector::ApplyBearerIfPossible(TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request) const
{
	const FString Tok = TherapistJwtToken.TrimStartAndEnd();
	if (Tok.IsEmpty())
	{
		UE_LOG(LogTemp, Error,
			TEXT("[YourMove] TherapistJwtToken empty — login via web or POST /api/auth/login, paste JWT here."));
		return false;
	}
	Request->SetHeader(TEXT("Authorization"), FString::Printf(TEXT("Bearer %s"), *Tok));
	return true;
}

void UYourMoveConnector::ValidateAccessKey(const FString& DoctorDisplayName, const FString& AccessKey)
{
	SavedAccessKey = AccessKey;

	if (TherapistJwtToken.TrimStartAndEnd().IsEmpty())
	{
		OnSessionValidated.Broadcast(false, TEXT(""), TEXT("TherapistJwtToken required (Bearer) for /api/sessions/start"));
		return;
	}

	const FString URL = BuildHttpBaseUrl() + TEXT("/api/sessions/start");

	TSharedRef<FJsonObject> Body = MakeShared<FJsonObject>();
	Body->SetStringField(TEXT("access_key"), AccessKey);
	if (!DoctorDisplayName.IsEmpty())
	{
		Body->SetStringField(TEXT("doctor_name"), DoctorDisplayName);
	}

	FString BodyString;
	TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&BodyString);
	FJsonSerializer::Serialize(Body, Writer);

	TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = FHttpModule::Get().CreateRequest();
	Request->SetURL(URL);
	Request->SetVerb(TEXT("POST"));
	Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
	if (!ApplyBearerIfPossible(Request))
	{
		OnSessionValidated.Broadcast(false, TEXT(""), TEXT("Missing TherapistJwtToken"));
		return;
	}
	Request->SetContentAsString(BodyString);

	Request->OnProcessRequestComplete().BindLambda(
		[this](FHttpRequestPtr Req, FHttpResponsePtr Resp, bool bSuccess)
		{
			if (!bSuccess || !Resp.IsValid())
			{
				OnSessionValidated.Broadcast(false, TEXT(""), TEXT("HTTP network error"));
				return;
			}

			const int32 Code = Resp->GetResponseCode();
			const FString ResponseBody = Resp->GetContentAsString();

			if (Code < 200 || Code >= 300)
			{
				UE_LOG(LogTemp, Error, TEXT("[YourMove] /api/sessions/start failed %d: %s"), Code, *ResponseBody);
				OnSessionValidated.Broadcast(false, TEXT(""), ResponseBody);
				return;
			}

			TSharedPtr<FJsonObject> JsonObj;
			TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(ResponseBody);
			if (!FJsonSerializer::Deserialize(Reader, JsonObj) || !JsonObj.IsValid())
			{
				OnSessionValidated.Broadcast(false, TEXT(""), TEXT("Invalid JSON from server"));
				return;
			}

			double SidNum = 0.0;
			if (JsonObj->TryGetNumberField(TEXT("session_id"), SidNum))
			{
				SessionID = FString::FromInt((int32)SidNum);
			}
			else
			{
				SessionID = JsonObj->GetStringField(TEXT("session_id"));
			}

			if (JsonObj->HasField(TEXT("patient_name")))
			{
				PatientName = JsonObj->GetStringField(TEXT("patient_name"));
			}
			if (JsonObj->HasField(TEXT("baseline_duration_seconds")))
			{
				BaselineDuration = (float)JsonObj->GetNumberField(TEXT("baseline_duration_seconds"));
			}

			FString SensoryJSON;
			if (JsonObj->HasField(TEXT("sensory_profile")))
			{
				TSharedPtr<FJsonObject> SensoryObj = JsonObj->GetObjectField(TEXT("sensory_profile"));
				if (SensoryObj.IsValid())
				{
					TSharedRef<TJsonWriter<>> SWriter = TJsonWriterFactory<>::Create(&SensoryJSON);
					FJsonSerializer::Serialize(SensoryObj.ToSharedRef(), SWriter);
				}
			}

			UE_LOG(LogTemp, Log, TEXT("[YourMove] Session started id=%s patient=%s"), *SessionID, *PatientName);
			OnSessionValidated.Broadcast(true, SessionID, SensoryJSON);
			ConnectWebSocket();
		});

	Request->ProcessRequest();
}

void UYourMoveConnector::ConnectWebSocket()
{
	if (SessionID.IsEmpty())
	{
		UE_LOG(LogTemp, Error, TEXT("[YourMove] ConnectWebSocket: SessionID empty"));
		return;
	}
	if (TherapistJwtToken.TrimStartAndEnd().IsEmpty())
	{
		UE_LOG(LogTemp, Error, TEXT("[YourMove] ConnectWebSocket: TherapistJwtToken empty"));
		return;
	}

	const FString CleanSessionID = SessionID.Replace(TEXT("$"), TEXT("")).TrimStartAndEnd();
	const FString URL = BuildWebSocketUrl(CleanSessionID);

	UE_LOG(LogTemp, Log, TEXT("[YourMove] WebSocket URL (token hidden): %s://%s/ws/ue5/%s?token=***"),
		bUseTLS ? TEXT("wss") : TEXT("ws"), *ServerHost, *CleanSessionID);

	SetConnectionState(EYourMoveState::Connecting);

	WebSocket = FWebSocketsModule::Get().CreateWebSocket(URL, FString());

	WebSocket->OnConnected().AddLambda([this]() { OnWebSocketConnected(); });
	WebSocket->OnConnectionError().AddLambda([this](const FString& Error) { OnWebSocketConnectionError(Error); });
	WebSocket->OnClosed().AddLambda(
		[this](int32 StatusCode, const FString& Reason, bool bWasClean) { OnWebSocketClosed(StatusCode, Reason, bWasClean); });
	WebSocket->OnMessage().AddLambda([this](const FString& Message) { OnWebSocketMessage(Message); });

	WebSocket->Connect();
}

void UYourMoveConnector::StartBaseline()
{
	bIsBaselinePhase = true;
	BaselineElapsed = 0.0f;
	BaselineTimeRemaining = BaselineDuration;
	SetConnectionState(EYourMoveState::InBaseline);

	TSharedRef<FJsonObject> Msg = MakeShared<FJsonObject>();
	Msg->SetStringField(TEXT("type"), TEXT("session_event"));
	Msg->SetStringField(TEXT("event"), TEXT("baseline_start"));
	Msg->SetStringField(TEXT("timestamp"), GetTimestamp());
	SendJSON(Msg);
}

void UYourMoveConnector::EndBaseline()
{
	if (!bIsBaselinePhase)
	{
		return;
	}
	bIsBaselinePhase = false;
	SetConnectionState(EYourMoveState::InSession);

	TSharedRef<FJsonObject> Msg = MakeShared<FJsonObject>();
	Msg->SetStringField(TEXT("type"), TEXT("session_event"));
	Msg->SetStringField(TEXT("event"), TEXT("baseline_end"));
	Msg->SetStringField(TEXT("timestamp"), GetTimestamp());
	SendJSON(Msg);
}

void UYourMoveConnector::StartActivity(EYourMoveActivity Activity)
{
	CurrentActivity = Activity;
	TSharedRef<FJsonObject> Msg = MakeShared<FJsonObject>();
	Msg->SetStringField(TEXT("type"), TEXT("session_event"));
	Msg->SetStringField(TEXT("event"), TEXT("activity_start"));
	Msg->SetStringField(TEXT("activity_type"), ActivityToString(Activity));
	Msg->SetStringField(TEXT("timestamp"), GetTimestamp());
	SendJSON(Msg);
}

void UYourMoveConnector::EndActivity(int32 FinalScore, int32 TotalRounds)
{
	TSharedRef<FJsonObject> Msg = MakeShared<FJsonObject>();
	Msg->SetStringField(TEXT("type"), TEXT("session_event"));
	Msg->SetStringField(TEXT("event"), TEXT("activity_end"));
	Msg->SetStringField(TEXT("activity_type"), ActivityToString(CurrentActivity));
	Msg->SetNumberField(TEXT("final_score"), FinalScore);
	Msg->SetNumberField(TEXT("total_rounds"), TotalRounds);
	Msg->SetStringField(TEXT("timestamp"), GetTimestamp());
	SendJSON(Msg);
	CurrentActivity = EYourMoveActivity::None;
}

void UYourMoveConnector::EndSession()
{
	TSharedRef<FJsonObject> Msg = MakeShared<FJsonObject>();
	Msg->SetStringField(TEXT("type"), TEXT("session_event"));
	Msg->SetStringField(TEXT("event"), TEXT("session_end"));
	Msg->SetStringField(TEXT("timestamp"), GetTimestamp());
	SendJSON(Msg);
	bShouldReconnect = false;

	FTimerHandle TimerHandle;
	if (GetWorld())
	{
		GetWorld()->GetTimerManager().SetTimer(TimerHandle, [this]() { Disconnect(); }, 1.0f, false);
	}
}

void UYourMoveConnector::Disconnect()
{
	bShouldReconnect = false;
	if (WebSocket.IsValid() && WebSocket->IsConnected())
	{
		WebSocket->Close();
	}
	WebSocket.Reset();
	SetConnectionState(EYourMoveState::Disconnected);
	SessionID.Empty();
}

void UYourMoveConnector::MarkTargetAppeared()
{
	TargetAppearedTime = FPlatformTime::Seconds();
	bWaitingForInteraction = true;
}

float UYourMoveConnector::RecordInteraction(bool bIsCorrect, int32 Round, int32 Score, int32 DifficultyLevel)
{
	float ReactionTimeMs = 0.0f;
	if (bWaitingForInteraction)
	{
		const double Now = FPlatformTime::Seconds();
		ReactionTimeMs = static_cast<float>((Now - TargetAppearedTime) * 1000.0);
		bWaitingForInteraction = false;
	}

	TSharedRef<FJsonObject> Msg = MakeShared<FJsonObject>();
	Msg->SetStringField(TEXT("type"), TEXT("game_event"));
	Msg->SetStringField(TEXT("timestamp"), GetTimestamp());
	Msg->SetStringField(TEXT("activity_type"), ActivityToString(CurrentActivity));

	TSharedRef<FJsonObject> Data = MakeShared<FJsonObject>();
	Data->SetStringField(TEXT("event"), TEXT("interaction"));
	Data->SetNumberField(TEXT("reaction_time_ms"), ReactionTimeMs);
	Data->SetBoolField(TEXT("is_correct"), bIsCorrect);
	Data->SetNumberField(TEXT("round"), Round);
	Data->SetNumberField(TEXT("score"), Score);
	Data->SetNumberField(TEXT("difficulty_level"), DifficultyLevel);
	Data->SetBoolField(TEXT("is_baseline"), bIsBaselinePhase);
	Msg->SetObjectField(TEXT("data"), Data);

	SendJSON(Msg);
	return ReactionTimeMs;
}

void UYourMoveConnector::RecordOmission(int32 Round)
{
	bWaitingForInteraction = false;
	TSharedRef<FJsonObject> Msg = MakeShared<FJsonObject>();
	Msg->SetStringField(TEXT("type"), TEXT("game_event"));
	Msg->SetStringField(TEXT("timestamp"), GetTimestamp());
	Msg->SetStringField(TEXT("activity_type"), ActivityToString(CurrentActivity));

	TSharedRef<FJsonObject> Data = MakeShared<FJsonObject>();
	Data->SetStringField(TEXT("event"), TEXT("omission"));
	Data->SetNumberField(TEXT("round"), Round);
	Data->SetBoolField(TEXT("is_baseline"), bIsBaselinePhase);
	Msg->SetObjectField(TEXT("data"), Data);

	SendJSON(Msg);
}

void UYourMoveConnector::SendCustomGameEvent(const FString& EventName, const TMap<FString, FString>& ExtraData)
{
	TSharedRef<FJsonObject> Msg = MakeShared<FJsonObject>();
	Msg->SetStringField(TEXT("type"), TEXT("game_event"));
	Msg->SetStringField(TEXT("timestamp"), GetTimestamp());
	Msg->SetStringField(TEXT("activity_type"), ActivityToString(CurrentActivity));

	TSharedRef<FJsonObject> Data = MakeShared<FJsonObject>();
	Data->SetStringField(TEXT("event"), EventName);
	Data->SetBoolField(TEXT("is_baseline"), bIsBaselinePhase);
	for (const auto& Pair : ExtraData)
	{
		Data->SetStringField(Pair.Key, Pair.Value);
	}
	Msg->SetObjectField(TEXT("data"), Data);
	SendJSON(Msg);
}

void UYourMoveConnector::SendMotionData(const FYourMoveAllTrackers& Trackers, float TrackerConfidence)
{
	const float TotalMovement = ComputeTotalMovementIndex(Trackers);

	TSharedRef<FJsonObject> Msg = MakeShared<FJsonObject>();
	Msg->SetStringField(TEXT("type"), TEXT("motion_data"));
	Msg->SetStringField(TEXT("timestamp"), GetTimestamp());

	TSharedRef<FJsonObject> Data = MakeShared<FJsonObject>();
	TSharedRef<FJsonObject> TrackersObj = MakeShared<FJsonObject>();

	auto AddTracker = [&TrackersObj](const FString& Name, const FYourMoveTrackerData& T)
	{
		TSharedRef<FJsonObject> TObj = MakeShared<FJsonObject>();
		TArray<TSharedPtr<FJsonValue>> QuatArr;
		QuatArr.Add(MakeShared<FJsonValueNumber>(T.Quaternion.X));
		QuatArr.Add(MakeShared<FJsonValueNumber>(T.Quaternion.Y));
		QuatArr.Add(MakeShared<FJsonValueNumber>(T.Quaternion.Z));
		QuatArr.Add(MakeShared<FJsonValueNumber>(T.Quaternion.W));
		TObj->SetArrayField(TEXT("quat"), QuatArr);
		TObj->SetNumberField(TEXT("accel_magnitude"), T.AccelMagnitude);
		TrackersObj->SetObjectField(Name, TObj);
	};

	AddTracker(TEXT("head"), Trackers.Head);
	AddTracker(TEXT("chest"), Trackers.Chest);
	AddTracker(TEXT("left_upper_arm"), Trackers.LeftUpperArm);
	AddTracker(TEXT("right_upper_arm"), Trackers.RightUpperArm);
	AddTracker(TEXT("left_lower_arm"), Trackers.LeftLowerArm);
	AddTracker(TEXT("right_lower_arm"), Trackers.RightLowerArm);
	AddTracker(TEXT("left_hand"), Trackers.LeftHand);
	AddTracker(TEXT("right_hand"), Trackers.RightHand);
	AddTracker(TEXT("left_upper_leg"), Trackers.LeftUpperLeg);
	AddTracker(TEXT("right_upper_leg"), Trackers.RightUpperLeg);
	AddTracker(TEXT("left_lower_leg"), Trackers.LeftLowerLeg);
	AddTracker(TEXT("right_lower_leg"), Trackers.RightLowerLeg);
	AddTracker(TEXT("left_foot"), Trackers.LeftFoot);
	AddTracker(TEXT("right_foot"), Trackers.RightFoot);

	Data->SetObjectField(TEXT("trackers"), TrackersObj);
	Data->SetNumberField(TEXT("total_movement_index"), TotalMovement);
	Data->SetNumberField(TEXT("tracker_confidence"), TrackerConfidence);
	Data->SetBoolField(TEXT("is_baseline"), bIsBaselinePhase);
	Msg->SetObjectField(TEXT("data"), Data);

	SendJSON(Msg);
	PreviousTrackers = Trackers;
	bHasPreviousTrackers = true;
}

float UYourMoveConnector::ComputeTotalMovementIndex(const FYourMoveAllTrackers& Current)
{
	if (!bHasPreviousTrackers)
	{
		return 0.0f;
	}
	float Total = 0.0f;
	auto QuatDelta = [](const FQuat& A, const FQuat& B) -> float
	{
		float Dot = FMath::Abs(A | B);
		Dot = FMath::Clamp(Dot, 0.0f, 1.0f);
		return FMath::RadiansToDegrees(2.0f * FMath::Acos(Dot));
	};
	Total += QuatDelta(Current.Chest.Quaternion, PreviousTrackers.Chest.Quaternion);
	Total += QuatDelta(Current.LeftUpperArm.Quaternion, PreviousTrackers.LeftUpperArm.Quaternion);
	Total += QuatDelta(Current.RightUpperArm.Quaternion, PreviousTrackers.RightUpperArm.Quaternion);
	Total += QuatDelta(Current.LeftLowerArm.Quaternion, PreviousTrackers.LeftLowerArm.Quaternion);
	Total += QuatDelta(Current.RightLowerArm.Quaternion, PreviousTrackers.RightLowerArm.Quaternion);
	Total += QuatDelta(Current.LeftUpperLeg.Quaternion, PreviousTrackers.LeftUpperLeg.Quaternion);
	Total += QuatDelta(Current.RightUpperLeg.Quaternion, PreviousTrackers.RightUpperLeg.Quaternion);
	Total += QuatDelta(Current.LeftLowerLeg.Quaternion, PreviousTrackers.LeftLowerLeg.Quaternion);
	Total += QuatDelta(Current.RightLowerLeg.Quaternion, PreviousTrackers.RightLowerLeg.Quaternion);
	Total += QuatDelta(Current.LeftFoot.Quaternion, PreviousTrackers.LeftFoot.Quaternion);
	Total += QuatDelta(Current.RightFoot.Quaternion, PreviousTrackers.RightFoot.Quaternion);
	return Total;
}

void UYourMoveConnector::SendHeadGaze(FRotator HMDRotation, FVector HMDPosition, bool bIsLookingAtTarget,
	float AngleToDegrees)
{
	TSharedRef<FJsonObject> Msg = MakeShared<FJsonObject>();
	Msg->SetStringField(TEXT("type"), TEXT("head_gaze"));
	Msg->SetStringField(TEXT("timestamp"), GetTimestamp());

	TSharedRef<FJsonObject> Data = MakeShared<FJsonObject>();
	TSharedRef<FJsonObject> HMDRot = MakeShared<FJsonObject>();
	HMDRot->SetNumberField(TEXT("pitch"), HMDRotation.Pitch);
	HMDRot->SetNumberField(TEXT("yaw"), HMDRotation.Yaw);
	HMDRot->SetNumberField(TEXT("roll"), HMDRotation.Roll);
	Data->SetObjectField(TEXT("hmd_rotation"), HMDRot);

	TSharedRef<FJsonObject> HMDPos = MakeShared<FJsonObject>();
	HMDPos->SetNumberField(TEXT("x"), HMDPosition.X);
	HMDPos->SetNumberField(TEXT("y"), HMDPosition.Y);
	HMDPos->SetNumberField(TEXT("z"), HMDPosition.Z);
	Data->SetObjectField(TEXT("hmd_position"), HMDPos);

	Data->SetBoolField(TEXT("is_looking_at_target"), bIsLookingAtTarget);
	Data->SetNumberField(TEXT("angle_to_target_degrees"), AngleToDegrees);
	Data->SetBoolField(TEXT("is_baseline"), bIsBaselinePhase);
	Msg->SetObjectField(TEXT("data"), Data);

	SendJSON(Msg);
}

void UYourMoveConnector::OnWebSocketConnected()
{
	UE_LOG(LogTemp, Log, TEXT("[YourMove] WebSocket connected"));
	SetConnectionState(EYourMoveState::InSession);
	bShouldReconnect = true;
	ReconnectTimer = 0.0f;
	FlushQueue();

	TSharedRef<FJsonObject> Msg = MakeShared<FJsonObject>();
	Msg->SetStringField(TEXT("type"), TEXT("session_event"));
	Msg->SetStringField(TEXT("event"), TEXT("session_start"));
	Msg->SetStringField(TEXT("timestamp"), GetTimestamp());
	SendJSON(Msg);
}

void UYourMoveConnector::OnWebSocketConnectionError(const FString& Error)
{
	UE_LOG(LogTemp, Error, TEXT("[YourMove] WebSocket error: %s"), *Error);
	SetConnectionState(EYourMoveState::Disconnected);
}

void UYourMoveConnector::OnWebSocketClosed(int32 StatusCode, const FString& Reason, bool bWasClean)
{
	UE_LOG(LogTemp, Warning, TEXT("[YourMove] WebSocket closed %d %s"), StatusCode, *Reason);
	SetConnectionState(EYourMoveState::Disconnected);
}

void UYourMoveConnector::OnWebSocketMessage(const FString& Message)
{
	TSharedPtr<FJsonObject> JsonObj;
	TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Message);
	if (!FJsonSerializer::Deserialize(Reader, JsonObj) || !JsonObj.IsValid())
	{
		return;
	}

	const FString Type = JsonObj->GetStringField(TEXT("type"));
	if (Type == TEXT("doctor_command"))
	{
		const FString Command = JsonObj->GetStringField(TEXT("command"));
		float Value = 0.0f;
		if (JsonObj->HasField(TEXT("value")))
		{
			double N = 0.0;
			if (JsonObj->TryGetNumberField(TEXT("value"), N))
			{
				Value = (float)N;
			}
			else
			{
				Value = FCString::Atof(*JsonObj->GetStringField(TEXT("value")));
			}
		}
		const FString Extra = JsonObj->HasField(TEXT("extra")) ? JsonObj->GetStringField(TEXT("extra")) : FString();
		OnDoctorCommand.Broadcast(Command, Value, Extra);
	}
	else if (Type == TEXT("ai_command"))
	{
		const FString Command = JsonObj->GetStringField(TEXT("command"));
		const float Value = (float)JsonObj->GetNumberField(TEXT("value"));
		const FString R = JsonObj->HasField(TEXT("reason")) ? JsonObj->GetStringField(TEXT("reason")) : FString();
		OnAICommand.Broadcast(Command, Value, R);
	}
	else if (Type == TEXT("session_config"))
	{
		OnSessionValidated.Broadcast(true, SessionID, Message);
	}
}

void UYourMoveConnector::SendJSON(const TSharedRef<FJsonObject>& JsonObject)
{
	FString OutputString;
	TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&OutputString);
	FJsonSerializer::Serialize(JsonObject, Writer);
	SendOrQueue(OutputString);
}

void UYourMoveConnector::SendOrQueue(const FString& JsonString)
{
	if (WebSocket.IsValid() && WebSocket->IsConnected())
	{
		FlushQueue();
		WebSocket->Send(JsonString);
	}
	else
	{
		MessageQueue.Add(JsonString);
		if (MessageQueue.Num() > MAX_QUEUE_SIZE)
		{
			MessageQueue.RemoveAt(0);
		}
	}
}

void UYourMoveConnector::FlushQueue()
{
	if (!WebSocket.IsValid() || !WebSocket->IsConnected())
	{
		return;
	}
	for (const FString& Msg : MessageQueue)
	{
		WebSocket->Send(Msg);
	}
	MessageQueue.Empty();
}

FString UYourMoveConnector::GetTimestamp()
{
	return FString::SanitizeFloat(FPlatformTime::Seconds());
}

FString UYourMoveConnector::ActivityToString(EYourMoveActivity Activity)
{
	switch (Activity)
	{
	case EYourMoveActivity::ShellGame: return TEXT("ShellGame");
	case EYourMoveActivity::HitTheOrder: return TEXT("HitTheOrder");
	case EYourMoveActivity::TrackTheTarget: return TEXT("TrackTheTarget");
	case EYourMoveActivity::AnimalsGame: return TEXT("AnimalsGame");
	case EYourMoveActivity::BoxesGame: return TEXT("BoxesGame");
	case EYourMoveActivity::Baseline: return TEXT("Baseline");
	default: return TEXT("None");
	}
}

void UYourMoveConnector::SetConnectionState(EYourMoveState NewState)
{
	if (ConnectionState != NewState)
	{
		ConnectionState = NewState;
		OnConnectionChanged.Broadcast(NewState);
	}
}
