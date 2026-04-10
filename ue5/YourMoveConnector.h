// YourMoveConnector.h
// ═══════════════════════════════════════════════════════════
// YourMove — UE5 ↔ FastAPI Bridge (matches app/api + app/websocket)
//
// Setup:
// 1) Therapist logs in via web → copy JWT (or use dev token from /api/auth/login).
// 2) Paste into TherapistJwtToken in Details.
// 3) Set ServerHost / ServerPort / bUseTLS for local (http://127.0.0.1:8000) or Koyeb (https host, TLS on).
// 4) ValidateAccessKey(DoctorDisplayName, PatientAccessKey) → starts session + opens WebSocket.
//
// Add WebSockets + HTTP modules to YourProject.Build.cs:
//   PublicDependencyModuleNames.AddRange(new[] { "WebSockets", "HTTP" });
// ═══════════════════════════════════════════════════════════

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "IWebSocket.h"
#include "Dom/JsonObject.h"
#include "YourMoveConnector.generated.h"

UENUM(BlueprintType)
enum class EYourMoveActivity : uint8
{
	ShellGame UMETA(DisplayName = "ShellGame"),
	HitTheOrder UMETA(DisplayName = "HitTheOrder"),
	TrackTheTarget UMETA(DisplayName = "TrackTheTarget"),
	AnimalsGame UMETA(DisplayName = "AnimalsGame"),
	BoxesGame UMETA(DisplayName = "BoxesGame"),
	Baseline UMETA(DisplayName = "Baseline"),
	None UMETA(DisplayName = "None")
};

UENUM(BlueprintType)
enum class EYourMoveState : uint8
{
	Disconnected UMETA(DisplayName = "Disconnected"),
	Connecting UMETA(DisplayName = "Connecting"),
	Connected UMETA(DisplayName = "Connected"),
	InSession UMETA(DisplayName = "InSession"),
	InBaseline UMETA(DisplayName = "InBaseline")
};

USTRUCT(BlueprintType)
struct FYourMoveTrackerData
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadWrite, Category = "YourMove")
	FQuat Quaternion = FQuat::Identity;

	UPROPERTY(BlueprintReadWrite, Category = "YourMove")
	float AccelMagnitude = 0.0f;
};

USTRUCT(BlueprintType)
struct FYourMoveAllTrackers
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadWrite) FYourMoveTrackerData Head;
	UPROPERTY(BlueprintReadWrite) FYourMoveTrackerData Chest;
	UPROPERTY(BlueprintReadWrite) FYourMoveTrackerData LeftUpperArm;
	UPROPERTY(BlueprintReadWrite) FYourMoveTrackerData RightUpperArm;
	UPROPERTY(BlueprintReadWrite) FYourMoveTrackerData LeftLowerArm;
	UPROPERTY(BlueprintReadWrite) FYourMoveTrackerData RightLowerArm;
	UPROPERTY(BlueprintReadWrite) FYourMoveTrackerData LeftHand;
	UPROPERTY(BlueprintReadWrite) FYourMoveTrackerData RightHand;
	UPROPERTY(BlueprintReadWrite) FYourMoveTrackerData LeftUpperLeg;
	UPROPERTY(BlueprintReadWrite) FYourMoveTrackerData RightUpperLeg;
	UPROPERTY(BlueprintReadWrite) FYourMoveTrackerData LeftLowerLeg;
	UPROPERTY(BlueprintReadWrite) FYourMoveTrackerData RightLowerLeg;
	UPROPERTY(BlueprintReadWrite) FYourMoveTrackerData LeftFoot;
	UPROPERTY(BlueprintReadWrite) FYourMoveTrackerData RightFoot;
};

UCLASS(ClassGroup = (YourMove), meta = (BlueprintSpawnableComponent))
class UYourMoveConnector : public UActorComponent
{
	GENERATED_BODY()

public:
	UYourMoveConnector();
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
	virtual void TickComponent(float DeltaTime, ELevelTick TickType,
		FActorComponentTickFunction* ThisTickFunction) override;

	// ═══ CONFIG — Blueprint Details ═══

	/** e.g. 127.0.0.1 or my-app.koyeb.app (no scheme) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "YourMove|Config")
	FString ServerHost = TEXT("127.0.0.1");

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "YourMove|Config", meta = (ClampMin = "1", UIMin = "1"))
	int32 ServerPort = 8000;

	/** Off = ws/http (local). On = wss/https (Koyeb / production). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "YourMove|Config")
	bool bUseTLS = false;

	/**
	 * JWT from POST /api/auth/login (same as browser ym_token / access_token).
	 * Required for POST /api/sessions/start and WebSocket ?token=...
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "YourMove|Config")
	FString TherapistJwtToken;

	// ═══ STATE ═══

	UPROPERTY(BlueprintReadOnly, Category = "YourMove|State")
	FString SavedAccessKey;

	UPROPERTY(BlueprintReadOnly, Category = "YourMove|State")
	EYourMoveState ConnectionState = EYourMoveState::Disconnected;

	UPROPERTY(BlueprintReadOnly, Category = "YourMove|State")
	FString SessionID;

	UPROPERTY(BlueprintReadOnly, Category = "YourMove|State")
	FString PatientName;

	UPROPERTY(BlueprintReadOnly, Category = "YourMove|State")
	EYourMoveActivity CurrentActivity = EYourMoveActivity::None;

	UPROPERTY(BlueprintReadOnly, Category = "YourMove|State")
	bool bIsBaselinePhase = false;

	UPROPERTY(BlueprintReadOnly, Category = "YourMove|State")
	float BaselineTimeRemaining = 120.0f;

	// ═══ SESSION ═══

	/** POST /api/sessions/start with { access_key, doctor_name? } + Bearer token. Then connects WebSocket. */
	UFUNCTION(BlueprintCallable, Category = "YourMove|Session")
	void ValidateAccessKey(const FString& DoctorDisplayName, const FString& AccessKey);

	UFUNCTION(BlueprintCallable, Category = "YourMove|Session")
	void ConnectWebSocket();

	UFUNCTION(BlueprintCallable, Category = "YourMove|Session")
	void StartBaseline();

	UFUNCTION(BlueprintCallable, Category = "YourMove|Session")
	void EndBaseline();

	UFUNCTION(BlueprintCallable, Category = "YourMove|Session")
	void StartActivity(EYourMoveActivity Activity);

	UFUNCTION(BlueprintCallable, Category = "YourMove|Session")
	void EndActivity(int32 FinalScore, int32 TotalRounds);

	UFUNCTION(BlueprintCallable, Category = "YourMove|Session")
	void EndSession();

	UFUNCTION(BlueprintCallable, Category = "YourMove|Session")
	void Disconnect();

	UFUNCTION(BlueprintCallable, Category = "YourMove|Game")
	void MarkTargetAppeared();

	UFUNCTION(BlueprintCallable, Category = "YourMove|Game")
	float RecordInteraction(bool bIsCorrect, int32 Round, int32 Score, int32 DifficultyLevel);

	UFUNCTION(BlueprintCallable, Category = "YourMove|Game")
	void RecordOmission(int32 Round);

	UFUNCTION(BlueprintCallable, Category = "YourMove|Game")
	void SendCustomGameEvent(const FString& EventName, const TMap<FString, FString>& ExtraData);

	UFUNCTION(BlueprintCallable, Category = "YourMove|Motion")
	void SendMotionData(const FYourMoveAllTrackers& Trackers, float TrackerConfidence);

	UFUNCTION(BlueprintCallable, Category = "YourMove|Gaze")
	void SendHeadGaze(FRotator HMDRotation, FVector HMDPosition, bool bIsLookingAtTarget, float AngleToDegrees);

	DECLARE_DYNAMIC_MULTICAST_DELEGATE_ThreeParams(FOnSessionValidated, bool, bSuccess, const FString&, InSessionID,
		const FString&, DetailOrSensoryJSON);
	UPROPERTY(BlueprintAssignable, Category = "YourMove|Events")
	FOnSessionValidated OnSessionValidated;

	DECLARE_DYNAMIC_MULTICAST_DELEGATE_ThreeParams(FOnDoctorCommand, const FString&, Command, float, Value,
		const FString&, Extra);
	UPROPERTY(BlueprintAssignable, Category = "YourMove|Events")
	FOnDoctorCommand OnDoctorCommand;

	DECLARE_DYNAMIC_MULTICAST_DELEGATE_ThreeParams(FOnAICommand, const FString&, Command, float, Value, const FString&,
		Reason);
	UPROPERTY(BlueprintAssignable, Category = "YourMove|Events")
	FOnAICommand OnAICommand;

	DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnConnectionChanged, EYourMoveState, NewState);
	UPROPERTY(BlueprintAssignable, Category = "YourMove|Events")
	FOnConnectionChanged OnConnectionChanged;

private:
	TSharedPtr<IWebSocket> WebSocket;

	TArray<FString> MessageQueue;
	static const int32 MAX_QUEUE_SIZE = 600;

	double TargetAppearedTime = 0.0;
	bool bWaitingForInteraction = false;

	FYourMoveAllTrackers PreviousTrackers;
	bool bHasPreviousTrackers = false;
	float ComputeTotalMovementIndex(const FYourMoveAllTrackers& Current);

	float BaselineElapsed = 0.0f;
	float BaselineDuration = 120.0f;

	float ReconnectTimer = 0.0f;
	float ReconnectInterval = 2.0f;
	bool bShouldReconnect = false;

	void SendJSON(const TSharedRef<FJsonObject>& JsonObject);
	void SendOrQueue(const FString& JsonString);
	void FlushQueue();
	FString GetTimestamp();
	FString ActivityToString(EYourMoveActivity Activity);
	void SetConnectionState(EYourMoveState NewState);

	FString BuildHttpBaseUrl() const;
	FString BuildWebSocketUrl(const FString& CleanSessionId) const;
	bool ApplyBearerIfPossible(TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request) const;

	float DataSendTimer = 0.0f;
	float DataSendInterval = 1.0f;
};
