package rest

import (
	"bytes"
	"encoding/json"
	"encoding/xml"
	"fmt"
	"io"
	"math"
	"net/http"
	"strconv"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"golang.org/x/exp/rand"
)

const CLIENT_USE_THRESHOLD = 5
const CLIENT_USE_RESET_TIME = time.Minute * 5
const (
	OPEN_ROUTE_BASE_URL = "https://api.openrouteservice.org/v2/directions/"
	API_KEY             = "5b3ce3597851110001cf6248131e72cedf2e4c9088dd6f792dc8c200"
)

type RouteType string

const (
	Cycling     RouteType = "cycling-road"
	FootWalking RouteType = "foot-walking"
)

type Marker struct {
	Lat float64 `json:"lat"`
	Lon float64 `json:"lon"`
}

type ClientInfo struct {
	Count    int
	LastSeen time.Time
}

type GenerateGPXRequest struct {
	StartCoords struct {
		Lat float64 `json:"lat"`
		Lon float64 `json:"lon"`
	} `json:"startCoords"`
	RouteLength int    `json:"routeLength"`
	RouteType   string `json:"routeType"`
}

type GPX struct {
	XMLName           xml.Name `xml:"gpx"`
	Version           string   `xml:"version,attr"`
	Creator           string   `xml:"creator,attr"`
	Xmlns             string   `xml:"xmlns,attr"`
	XmlnsXsi          string   `xml:"xmlns:xsi,attr"`
	XmlnsNs3          string   `xml:"xmlns:ns3,attr"`
	XmlnsNs2          string   `xml:"xmlns:ns2,attr"`
	XsiSchemaLocation string   `xml:"xsi:schemaLocation,attr"`
	Metadata          Metadata `xml:"metadata"`
	Trk               Trk      `xml:"trk"`
}

type Metadata struct {
	Link Link   `xml:"link"`
	Time string `xml:"time"`
}

type Link struct {
	Href string `xml:"href,attr"`
	Text string `xml:"text"`
}

type Trk struct {
	Name   string `xml:"name"`
	Type   string `xml:"type"`
	Trkseg Trkseg `xml:"trkseg"`
}

type Trkseg struct {
	Trkpts []Trkpt `xml:"trkpt"`
}

type Trkpt struct {
	Lat        float64     `xml:"lat,attr"`
	Lon        float64     `xml:"lon,attr"`
	Ele        float64     `xml:"ele"`
	Time       string      `xml:"time"`
	Extensions *Extensions `xml:"extensions,omitempty"`
}

type Extensions struct {
	TPE *TrackPointExtension `xml:"TrackPointExtension"`
}

type TrackPointExtension struct {
	XMLName xml.Name `xml:"TrackPointExtension"`
	Hr      int      `xml:"hr,omitempty"`
	Cad     int      `xml:"cad,omitempty"`
}

type GenerateFileRequest struct {
	Markers   []Marker `json:"markers"`
	Length    int      `json:"length"`
	RouteType string   `json:"route_type"`
}

type Handler struct {
	client_counter map[string]ClientInfo
	mu             sync.Mutex
}

func NewHandler() *Handler {
	return &Handler{
		client_counter: make(map[string]ClientInfo),
	}
}

func (h *Handler) Middleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		clientIP := c.ClientIP()
		h.mu.Lock()
		clientInfo, exists := h.client_counter[clientIP]
		if exists {
			if clientInfo.Count >= CLIENT_USE_THRESHOLD {
				h.mu.Unlock()
				c.AbortWithStatusJSON(429, gin.H{"error": "Too many requests"})
				return
			}
			clientInfo.Count++
			clientInfo.LastSeen = time.Now()
			h.client_counter[clientIP] = clientInfo
		} else {
			h.client_counter[clientIP] = ClientInfo{Count: 1, LastSeen: time.Now()}
			go h.resetClientCounter(clientIP)
		}
		h.mu.Unlock()
		c.Next()
	}
}

func (h *Handler) resetClientCounter(clientIP string) {
	time.Sleep(CLIENT_USE_RESET_TIME)
	h.mu.Lock()
	defer h.mu.Unlock()
	clientInfo, exists := h.client_counter[clientIP]
	if exists {
		if time.Since(clientInfo.LastSeen) >= CLIENT_USE_RESET_TIME {
			delete(h.client_counter, clientIP)
		} else {
			clientInfo.Count = 0
			h.client_counter[clientIP] = clientInfo
		}
	}
}

type GPXDataResult struct {
	Timestamps  []time.Time  `json:"timestamps"`
	BPMProfile  []int        `json:"bpmProfile"`
	PaceProfile []float64    `json:"paceProfile"`
	Route       []Coordinate `json:"route"`
}

type Coordinate struct {
	Lat float64 `json:"lat"`
	Lon float64 `json:"lon"`
	Ele float64 `json:"ele"`
}

func (h *Handler) HandleGenerateFileSingleMarker(c *gin.Context) {
	var requestBody GenerateGPXRequest

	if err := c.ShouldBindJSON(&requestBody); err != nil {
		c.JSON(400, gin.H{"error": "Invalid request"})
		return
	}

	fmt.Println("Received request to generate GPX data")

	// Fetch GPX data for a round trip
	startCoords := [2]float64{requestBody.StartCoords.Lon, requestBody.StartCoords.Lat}
	routeLength := requestBody.RouteLength
	numPoints := 5
	routeType := requestBody.RouteType
	if routeType == "" {
		routeType = "foot-walking"
	}

	gpxData, err := fetchRoundTripRoute(startCoords, API_KEY, routeLength, numPoints, routeType)
	if err != nil {
		c.JSON(500, gin.H{"error": fmt.Sprintf("An error occurred while fetching GPX data: %v", err)})
		return
	}

	// Parse GPX data to extract coordinates
	points, err := parseGPX(gpxData)
	if err != nil {
		c.JSON(500, gin.H{"error": fmt.Sprintf("An error occurred while parsing GPX data: %v", err)})
		return
	}

	if len(points) == 0 {
		c.JSON(500, gin.H{"error": "No track points found in the route."})
		return
	}
	const AvgSpeed = 1.5 // m/s
	const AvgBPM = 120
	const AvgCadence = 80
	// Estimate total time based on average speed
	totalTimeSeconds := int(float64(routeLength) / AvgSpeed)

	// Create speed profile
	totalTimeSeconds = int(float64(totalTimeSeconds) * 1.3)
	speedProfile := createSpeedProfile(totalTimeSeconds, AvgSpeed, 0.2)

	// Extract elevation changes
	elevationChanges := []float64{}
	for i := 0; i < len(points)-1; i++ {
		eleChange := points[i+1].Ele - points[i].Ele
		distance := haversineDistance(points[i].Lat, points[i].Lon, points[i+1].Lat, points[i+1].Lon)
		numSeconds := int(distance / AvgSpeed)
		for j := 0; j < numSeconds; j++ {
			if numSeconds > 0 {
				elevationChanges = append(elevationChanges, eleChange/float64(numSeconds))
			} else {
				elevationChanges = append(elevationChanges, 0)
			}
		}
	}
	// Pad elevationChanges
	if len(elevationChanges) < totalTimeSeconds {
		for i := len(elevationChanges); i < totalTimeSeconds; i++ {
			elevationChanges = append(elevationChanges, 0)
		}
	} else {
		elevationChanges = elevationChanges[:totalTimeSeconds]
	}

	totalTimeSeconds = totalTimeSeconds - 2
	bpmProfileFloat := createBPMProfile(totalTimeSeconds, AvgBPM, AvgSpeed, speedProfile, elevationChanges)
	cadenceProfile := createCadenceProfile(totalTimeSeconds, AvgCadence, AvgSpeed, speedProfile, elevationChanges)

	// Interpolate route points
	interpolatedPoints := []Trkpt{}
	currentTime := 0
	for i := 0; i < len(points)-1; i++ {
		p1 := points[i]
		p2 := points[i+1]
		newPoints := interpolatePoints(p1, p2, speedProfile, totalTimeSeconds, currentTime)
		interpolatedPoints = append(interpolatedPoints, newPoints...)
		distance := haversineDistance(p1.Lat, p1.Lon, p2.Lat, p2.Lon)
		var duration int
		if speedProfile[currentTime] > 0 {
			duration = int(distance / speedProfile[currentTime])
		} else {
			duration = 1
		}
		currentTime += duration
		if currentTime >= totalTimeSeconds {
			break
		}
	}

	// Adjust profiles to match interpolated points
	totalInterpolated := len(interpolatedPoints)

	// Ensure bpmProfile has enough length
	if len(bpmProfileFloat) < totalInterpolated {
		lastBPM := bpmProfileFloat[len(bpmProfileFloat)-1]
		for i := len(bpmProfileFloat); i < totalInterpolated; i++ {
			bpmProfileFloat = append(bpmProfileFloat, lastBPM)
		}
	} else {
		bpmProfileFloat = bpmProfileFloat[:totalInterpolated]
	}

	// Ensure cadenceProfile has enough length
	if len(cadenceProfile) < totalInterpolated {
		lastCadence := cadenceProfile[len(cadenceProfile)-1]
		for i := len(cadenceProfile); i < totalInterpolated; i++ {
			cadenceProfile = append(cadenceProfile, lastCadence)
		}
	} else {
		cadenceProfile = cadenceProfile[:totalInterpolated]
	}

	// Generate timestamps (one second apart)
	startTime := time.Now()
	timestamps := generateTimestamps(totalInterpolated, 1, startTime)
	if len(timestamps) != totalInterpolated {
		c.JSON(500, gin.H{"error": "Mismatch between number of timestamps and interpolated points."})
		return
	}

	// Convert bpmProfileFloat to int
	bpmProfile := make([]int, totalInterpolated)
	for i, v := range bpmProfileFloat {
		bpmProfile[i] = int(v)
	}

	// Create pace profile (min/km) from speed profile
	// speedProfile length might differ from totalInterpolated slightly,
	// we use the shortest length to match final arrays.
	if len(speedProfile) > totalInterpolated {
		speedProfile = speedProfile[:totalInterpolated]
	}

	paceProfile := make([]float64, totalInterpolated)
	for i, s := range speedProfile {
		if s <= 0 {
			paceProfile[i] = 999.0 // something large if speed is zero
		} else {
			// pace(min/km) = (1/speed [s/m]) * 1000[m/km] * (1 min/60s) = 1000/(speed*60)
			paceProfile[i] = 1000.0 / (s * 60.0)
		}
	}

	// Create route array
	route := make([]Coordinate, totalInterpolated)
	for i, pt := range interpolatedPoints {
		route[i] = Coordinate{Lat: pt.Lat, Lon: pt.Lon, Ele: pt.Ele}
	}

	result := GPXDataResult{
		Timestamps:  timestamps,
		BPMProfile:  bpmProfile,
		PaceProfile: paceProfile,
		Route:       route,
	}

	c.JSON(200, result)
}

func generateTimestamps(numPoints int, intervalSeconds int, startTime time.Time) []time.Time {
	timestamps := make([]time.Time, numPoints)
	for i := 0; i < numPoints; i++ {
		timestamps[i] = startTime.Add(time.Duration(i*intervalSeconds) * time.Second)
	}
	return timestamps
}

func createCadenceProfile(totalSeconds int, avgCadence, avgSpeed float64, speedProfile, elevationChanges []float64) []float64 {
	cadence := make([]float64, totalSeconds)
	cadence[0] = avgCadence + float64(rand.Intn(3)-1)
	for t := 1; t < totalSeconds; t++ {
		speedDeviation := speedProfile[t] - avgSpeed
		cadenceSpeed := speedDeviation * 3
		var elevationChange float64
		if t < len(elevationChanges) {
			elevationChange = elevationChanges[t]
		}
		cadenceElevation := elevationChange * 2
		cadenceTotal := avgCadence + cadenceSpeed + cadenceElevation + float64(rand.Intn(3)-1)
		if cadenceTotal < 30 {
			cadenceTotal = 30
		} else if cadenceTotal > 150 {
			cadenceTotal = 150
		}
		cadence[t] = cadenceTotal
	}
	return cadence
}

func createBPMProfile(totalSeconds int, avgBPM, avgSpeed float64, speedProfile, elevationChanges []float64) []float64 {
	bpm := make([]float64, totalSeconds)
	bpm[0] = avgBPM - 20
	for t := 1; t < totalSeconds; t++ {
		progress := float64(t) / float64(totalSeconds)
		sigmoid := 1 / (1 + math.Exp(-12*(progress-0.2)))
		baseBPM := -20 + 20*sigmoid
		speedDeviation := speedProfile[t] - avgSpeed
		bpmSpeed := speedDeviation * 10
		var elevationChange float64
		if t < len(elevationChanges) {
			elevationChange = elevationChanges[t]
		}
		bpmElevation := elevationChange * 8
		bpmTotal := avgBPM + baseBPM + bpmSpeed + bpmElevation + float64(rand.Intn(3)-1)
		if bpmTotal < 60 {
			bpmTotal = 60
		} else if bpmTotal > 200 {
			bpmTotal = 200
		}
		bpm[t] = bpmTotal
	}
	return bpm
}

func createSpeedProfile(totalSeconds int, avgSpeed, speedDecrease float64) []float64 {
	t := make([]float64, totalSeconds)
	for i := 0; i < totalSeconds; i++ {
		t[i] = float64(i)
	}

	randomFluctuations := make([]float64, totalSeconds)
	for i := 0; i < totalSeconds; i++ {
		randomFluctuations[i] = rand.NormFloat64() * 1.8
	}
	randomFluctuations[0] = 0.2 * avgSpeed

	desiredSpeeds := make([]float64, totalSeconds)
	for i := 0; i < totalSeconds; i++ {
		desiredSpeeds[i] = avgSpeed + randomFluctuations[i]
	}

	speedProfile := make([]float64, totalSeconds)
	for i := 0; i < totalSeconds; i++ {
		linearDecline := (speedDecrease * float64(i)) / float64(totalSeconds)
		speedProfile[i] = desiredSpeeds[i] - linearDecline
	}

	minSpeed := avgSpeed * 0.90
	for i := 0; i < totalSeconds; i++ {
		if speedProfile[i] < minSpeed {
			speedProfile[i] = minSpeed
		}
	}

	return speedProfile
}

func interpolatePoints(p1, p2 Trkpt, speedProfile []float64, totalTime int, currentTime int) []Trkpt {
	distance := haversineDistance(p1.Lat, p1.Lon, p2.Lat, p2.Lon)
	if currentTime >= len(speedProfile) {
		currentTime = len(speedProfile) - 1
	}
	speed := speedProfile[currentTime]
	duration := distance / speed
	numSeconds := int(duration)
	if numSeconds == 0 {
		numSeconds = 1
	}

	eleDiff := p2.Ele - p1.Ele
	interpolatedPoints := []Trkpt{}
	bearing := calculateInitialCompassBearing([2]float64{p1.Lat, p1.Lon}, [2]float64{p2.Lat, p2.Lon})

	for i := 1; i <= numSeconds; i++ {
		fraction := float64(i) / float64(numSeconds)
		interpolatedDistance := speed * float64(i)
		interpolatedLat, interpolatedLon := destinationPoint(p1.Lat, p1.Lon, bearing, interpolatedDistance)
		interpolatedEle := p1.Ele + (eleDiff * fraction)
		interpolatedPoints = append(interpolatedPoints, Trkpt{
			Lat: interpolatedLat,
			Lon: interpolatedLon,
			Ele: interpolatedEle,
		})
	}
	return interpolatedPoints
}

func haversineDistance(lat1, lon1, lat2, lon2 float64) float64 {
	const EarthRadius = 6371000
	dLat := (lat2 - lat1) * math.Pi / 180.0
	dLon := (lon2 - lon1) * math.Pi / 180.0
	a := math.Sin(dLat/2)*math.Sin(dLat/2) + math.Cos(lat1*math.Pi/180.0)*math.Cos(lat2*math.Pi/180.0)*math.Sin(dLon/2)*math.Sin(dLon/2)
	c := 2 * math.Atan2(math.Sqrt(a), math.Sqrt(1-a))
	distance := EarthRadius * c
	return distance
}

func destinationPoint(lat1, lon1, bearing, distance float64) (float64, float64) {
	const EarthRadius = 6371000
	bearing = bearing * math.Pi / 180.0
	lat1 = lat1 * math.Pi / 180.0
	lon1 = lon1 * math.Pi / 180.0

	lat2 := math.Asin(math.Sin(lat1)*math.Cos(distance/EarthRadius) + math.Cos(lat1)*math.Sin(distance/EarthRadius)*math.Cos(bearing))
	lon2 := lon1 + math.Atan2(math.Sin(bearing)*math.Sin(distance/EarthRadius)*math.Cos(lat1), math.Cos(distance/EarthRadius)-math.Sin(lat1)*math.Sin(lat2))

	lat2 = lat2 * 180.0 / math.Pi
	lon2 = lon2 * 180.0 / math.Pi

	return lat2, lon2
}

func calculateInitialCompassBearing(pointA, pointB [2]float64) float64 {
	lat1 := pointA[0] * math.Pi / 180.0
	lat2 := pointB[0] * math.Pi / 180.0
	diffLong := (pointB[1] - pointA[1]) * math.Pi / 180.0

	x := math.Sin(diffLong) * math.Cos(lat2)
	y := math.Cos(lat1)*math.Sin(lat2) - math.Sin(lat1)*math.Cos(lat2)*math.Cos(diffLong)

	initialBearing := math.Atan2(x, y)
	initialBearing = initialBearing * 180.0 / math.Pi
	compassBearing := math.Mod(initialBearing+360.0, 360.0)
	return compassBearing
}

func parseGPX(gpxData string) ([]Trkpt, error) {
	type GPXParse struct {
		XMLName xml.Name `xml:"gpx"`
		Rte     struct {
			Rtepts []struct {
				Lat string `xml:"lat,attr"`
				Lon string `xml:"lon,attr"`
				Ele string `xml:"ele"`
			} `xml:"rtept"`
		} `xml:"rte"`
	}
	var gpx GPXParse
	err := xml.Unmarshal([]byte(gpxData), &gpx)
	if err != nil {
		return nil, err
	}
	var points []Trkpt
	for _, pt := range gpx.Rte.Rtepts {
		lat, err1 := strconv.ParseFloat(pt.Lat, 64)
		lon, err2 := strconv.ParseFloat(pt.Lon, 64)
		ele, err3 := strconv.ParseFloat(pt.Ele, 64)
		if err1 != nil || err2 != nil || err3 != nil {
			fmt.Printf("Invalid coordinate or elevation value: lat=%s, lon=%s, ele=%s. Skipping point.\n", pt.Lat, pt.Lon, pt.Ele)
			continue
		}
		points = append(points, Trkpt{
			Lat: lat,
			Lon: lon,
			Ele: ele,
		})
	}
	fmt.Printf("Parsed %d track points from GPX data.\n", len(points))
	return points, nil
}

func fetchRoundTripRoute(startCoords [2]float64, apiKey string, routeLength int, numPoints int, routeType string) (string, error) {
	url := fmt.Sprintf("https://api.openrouteservice.org/v2/directions/%s/gpx?gpxType=track", routeType)
	payload := map[string]interface{}{
		"coordinates": [][]float64{startCoords[:]},
		"options": map[string]interface{}{
			"round_trip": map[string]interface{}{
				"length": routeLength,
				"points": numPoints,
			},
		},
		"elevation":         true,
		"instructions":      false,
		"geometry_simplify": false,
	}
	payloadBytes, err := json.Marshal(payload)
	if err != nil {
		return "", err
	}

	req, err := http.NewRequest("POST", url, bytes.NewBuffer(payloadBytes))
	if err != nil {
		return "", err
	}

	req.Header.Set("Authorization", apiKey)
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		bodyBytes, _ := io.ReadAll(resp.Body)
		fmt.Println("Error fetching route:", resp.StatusCode, string(bodyBytes))
		return "", fmt.Errorf("Error fetching route: %d - %s", resp.StatusCode, string(bodyBytes))
	}

	bodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}

	fmt.Println("GPX data fetched successfully.")
	return string(bodyBytes), nil
}
